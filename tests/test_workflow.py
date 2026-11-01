from pathlib import Path
from tempfile import TemporaryDirectory
import json
import struct
import unittest
from unittest.mock import patch
from cohortframe.cli import doctor
from cohortframe.models import ValidationError
from cohortframe.workflow import preflight, preview, export_studio
from cohortframe.core import Store


def brief(**kw):
    return {'version':1,'name':'Preview','width':320,'height':180,'fps':24,
            'scenes':[{'id':'intro','title':'HELLO','duration':1.04}],**kw}


class WorkflowTests(unittest.TestCase):
    def test_preflight_quantises_without_changing_inputs(self):
        data=brief(); original=json.dumps(data)
        result=preflight(data)
        self.assertEqual(result['frames'],25)
        self.assertEqual(result['duration_seconds'],25/24)
        self.assertEqual(json.dumps(data),original)
        self.assertTrue(result['layout_checked'])

    def test_schema_valid_but_unrenderable_layout_fails(self):
        with self.assertRaises(ValidationError):preflight(brief(width=16,height=16))

    def test_audio_is_not_claimed_as_verified(self):
        result=preflight(brief(audio='missing.wav'))
        self.assertFalse(result['audio_checked']);self.assertTrue(result['warnings'])

    def test_preview_is_png_and_cannot_overwrite_directory(self):
        with TemporaryDirectory() as temp:
            folder=Path(temp)/'frames';result=preview(brief(),folder)
            data=Path(result['images'][0]).read_bytes()
            self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('!II',data[16:24]),(320,180))
            with self.assertRaises(ValidationError):preview(brief(),folder)
            self.assertEqual(Path(result['images'][0]).read_bytes(),data)

    def test_failed_preflight_leaves_no_output(self):
        with TemporaryDirectory() as temp:
            folder=Path(temp)/'frames'
            with self.assertRaises(ValidationError):preview(brief(width=16,height=16),folder)
            self.assertFalse(folder.exists())

    def test_offline_studio_has_all_required_assets(self):
        with TemporaryDirectory() as temp:
            folder=Path(temp)/'studio';result=export_studio(folder)
            self.assertTrue(Path(result['index']).is_file())
            for asset in ('app.js','model.js','style.css','mark.svg'):self.assertTrue((folder/asset).is_file())
            with self.assertRaises(ValidationError):export_studio(folder)

    def test_project_listing_survives_reopen(self):
        with TemporaryDirectory() as temp:
            project=Store(temp).create_project(brief())
            self.assertEqual(Store(temp).list_projects()[0]['id'],project['id'])

    def test_doctor_does_not_claim_ready_with_missing_encoder(self):
        from subprocess import CompletedProcess
        def fake(args,**kwargs):
            return CompletedProcess(args,0,stdout=' V..... libx264 H.264' if '-encoders' in args else 'test 1.0',stderr='')
        with patch('cohortframe.cli.shutil.which',return_value='/bin/test'),patch('cohortframe.cli.subprocess.run',side_effect=fake):
            result=doctor()
        self.assertFalse(result['ready']);self.assertTrue(result['encoders']['libx264']);self.assertFalse(result['encoders']['aac'])

if __name__=='__main__':unittest.main()
