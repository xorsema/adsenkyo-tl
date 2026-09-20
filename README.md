# America Daitouryou Senkyo – English fan translation

An unofficial English patch for the NES game *America Daitouryou Senkyo* (HECT, 1988). Work in progress (v0.1 beta).

## Playing it

You need your own copy of the Japanese ROM (SHA-1 `864974432D5132137B0B17B1B21BBC857A34FAE2`). Apply one of the patches in [`release/`](release/) with any IPS/BPS patcher (e.g. Floating IPS). The patches contain only changed bytes, no game data. See [`release/README.txt`](release/README.txt) for details and known issues.

## Status

Translated: about 256 in-game messages, the 10 profile screens, the title logo, the party labels and a new Latin font. Not done: several tile-index screens, the name-entry keyboard and other picture text. Emulator-tested only.

## Repository

This repo holds the tools and notes, not the game data. ROM dumps, disassembly and the Japanese script are deliberately not included (see `.gitignore`).

- `tools/` – Python pipeline: text extraction, English insertion with relocation, font, bitmap and title patching, patch building
- `src/nes.cfg` – linker config for the disassembly rebuild
- `notes/` – text-encoding and code-flow notes
- `release/` – the patches

Building needs Python 3, the original ROM at `rom/original.nes` and cc65 unpacked in `tools/cc65/`. Emulator testing uses BizHawk with the mcp-bizhawk Lua bridge, which is not included.

## Credits

Translation and ROM hacking by Claude (Anthropic), working with the project owner. Original game © HECT 1988. Not affiliated with or endorsed by HECT or its successors.
