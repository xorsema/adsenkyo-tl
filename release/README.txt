America Daitouryou Senkyo (Japan) - English patch
Version 0.1 BETA (work in progress)
=====================================================

WHAT THIS IS
An unofficial fan translation of the NES game "America Daitouryou Senkyo" (HECT, 1988).
This is an early beta: playable in places, NOT finished, NOT fully play-tested.

HOW TO USE
You need your own copy of the Japanese ROM. Apply ONE of the patches to it:
  America_Daitouryou_Senkyo_EN_v0.1-beta.ips   (Lunar IPS, Floating IPS, etc.)
  America_Daitouryou_Senkyo_EN_v0.1-beta.bps   (Floating IPS, beat, MultiPatch; checks the source ROM)
The patches contain only changed bytes; no game data is included.

SOURCE ROM (the one the patch is made for)
  File:   America Daitouryou Senkyo (Japan).nes   262,160 bytes (iNES, mapper 1 / MMC1, 128K PRG + 128K CHR)
  SHA-1:  864974432D5132137B0B17B1B21BBC857A34FAE2
  CRC32:  FFC0D0A0
PATCHED ROM SHOULD BE
  SHA-1:  F51D70D82BC8DF8B7484D96D6A798A67EE82A807
  CRC32:  871C1A1D

WHAT IS TRANSLATED IN THIS BETA
  * ~256 in-game messages (menus, campaign and survey screens, speeches, primaries, finance rules,
    election-night announcements, the oath, most state statistics)
  * The 10 candidate/staff profile screens
  * The title logo (AMERICA / PRESIDENTIAL ELECTION) and the party labels (REP. / DEM.)
  * A new 8x8 Latin font (replaces the kana tiles)

KNOWN ISSUES / NOT DONE
  * Other screens still show Japanese, and because the kana tiles were replaced by letters, any UNTRANSLATED
    kana text appears as garbled Latin characters. Known untranslated areas include several tile-index
    screens (roughly message ids 183-206, 213-244, 251-255 of table 1), the name-entry keyboard, and any
    other picture text not yet found.
  * Lines are wrapped for a 28-tile width. A few scenes start text further right, so some lines may still
    run into the screen edge or wrap awkwardly. Some messages are now taller than the Japanese originals.
  * Candidate names are best guesses from the katakana (Sasscher is a Thatcher parody; Dole, Jackson, Rader,
    Sanderson, Suzuki are inferred). They may change.
  * Not fully play-tested. Save/battery behaviour is unchanged by the patch but untested.
  * Tested only in emulators (BizHawk 2.11 and Mesen). Real hardware and flash carts are UNTESTED: the patch
    adds two small code hooks in the fixed bank and uses PRG bank 5 (an unused copy of the fixed bank) as
    text storage.

TECHNICAL NOTES (for hackers)
  * English messages that do not fit their original slot live in PRG bank 5; the text engine hooks at
    $DC26 (bank choice) and $F815 (text fetch) treat pointers >= $C000 as "bank 5 + offset".
  * Profile screens draw their text from CHR page 1 (scene page table at $CA4E repointed).
  * CHR pages changed: 0 (party sprites), 1, 2, 19 (text fonts), 8 (title logo).

CREDITS
  Translation and ROM hacking by Claude (Anthropic), working with the project owner.
  Original game (c) HECT 1988. This project is not affiliated with or endorsed by HECT or its successors.
