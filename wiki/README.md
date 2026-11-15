# Wiki publication source

[Read the complete whitepaper](Whitepaper.md). This is the versioned source for the
project's GitHub Wiki. It is an AI-assisted design synthesis, not independent
review or a claim that the ideal roadmap is already implemented. Existing project
rights and visibility remain unchanged.

## Publication state

On 15 November 2026, an anonymous read of the live Wiki found HEAD
`2dfbbb5f472e18153493d4c7bfaba5a49372c15b`. Its managed `Whitepaper.md`
matched the committed publication source at
[`8d3845dbe0a451329f40fe55aabdb824ef9fbe97`](https://github.com/Albertito-AI/cohortframe/blob/8d3845dbe0a451329f40fe55aabdb824ef9fbe97/wiki/Whitepaper.md)
byte for byte. The managed Home section also matched. This is a dated baseline
observation, not proof that a later source revision has been published.

After every source update, inspect the publisher result and read back the live
page against the accepted source. If a future Wiki is absent or must be rebuilt,
GitHub requires a first page before ordinary Git publication; the
[documented initialisation procedure](https://docs.github.com/en/communities/documenting-your-project-with-wikis/adding-or-editing-wiki-pages)
is a recovery instruction, not the current publication state.

The `Publish project whitepaper to Wiki` workflow runs after that initial Wiki
edit and after later source changes. It uses the repository-scoped workflow token.
Its summary reports `PUBLISHED`, `ALREADY_CURRENT` or
`BLOCKED_UNINITIALISED`; the last state means no Wiki page was published.
No paid service or third-party publishing action is used.

The publisher writes only its marked Whitepaper page and a marked, additive Home
section. It preserves other pages and Home text, refuses an existing unmarked
Whitepaper, and uses a non-forced push. Concurrent changes require reconciliation.
Edit the versioned source for future paper updates. The script never executes Wiki
content, changes visibility or grants new reuse rights.

GitHub's documented initialisation requirement:
https://docs.github.com/en/communities/documenting-your-project-with-wikis/adding-or-editing-wiki-pages
