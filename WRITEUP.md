# Rate Connect onboarding email: write-up

Alireza Pakseresht Koubijari · Email Development & Marketing Automation intern case study · October 2026

## Approach

I treated the Figma file as data: every size, colour and text style went into a spec before any code, so the build matches the 700px frame to the pixel. The email is one fluid table with inline styles and one media query; an app that drops the stylesheet still gets a working layout. Classic Outlook draws email with Word, so it gets its own layout, button and circles in VML inside conditional comments. `email-ampscript.html` is the same markup with AMPscript; `previews/` shows its output.

## What broke, and what I did

- **Outlook**, found by rendering through Word's engine, not by reading code: clipped circle digits, cropped icons, a hairline around the logo. Fixed with a zero-inset VML text box (six variants compared), separate cells for icons, and an opaque logo PNG.
- **Images:** my first exports cut the avatar's edge and left seams. Re-exported at 16x and averaged to 4x; 4 of 71,824 pixels now differ from Figma's export.
- **Dark mode**, most of the work: the Gmail apps and both Outlooks recoloured the light-only design. Every bug had one cause: something an app recolours (colour, text) next to something it never recolours (an image, a VML shape). I tested three or four fixes per problem in one email across nine app setups (`tests/RESULTS.md`). Result: the email declares `color-scheme: light only`, which the Gmail apps honour since October 2026, and in Outlook VML panels and a tiny background image hold the header white and the footer navy.
- **Android:** a larger text setting stretched the number circles into ovals, so they are now images exported from Figma, and the "Add a property" button grows with its text.
- **My wrong turns**, all logged: an Outlook rule that did nothing; an outline I added to the trivago logo, which altered the brand and was removed; and two days of workarounds before checking whether Gmail's dark mode could simply be switched off.

## Where the build leaves the design

System fonts instead of SF Pro, which email cannot load. A solid colour for the 70% black subtitle, since Outlook ignores transparency. The 700px width kept as drawn, at the cost of a fixed width in classic Outlook. Four problems in the Figma file itself corrected: an off-centre mobile logo, mobile banner text overflowing its frame, a clipped footer icon, and empty space inside the logo component. In dark mode, new Outlook still darkens the light sections (readable) and classic Outlook shows the footer links white.

## Testing

Chrome at five widths, Word's engine, a copy without the stylesheet, and a pre-flight script verified against seven broken files. Then real inboxes, light and dark: Gmail on the web, the Gmail app on iPhone and Android (also with an Outlook account), Apple Mail, classic and new Outlook. On 15 October the final build looked as designed in all of them.

## AMPscript (written, not executed)

One property gives the email as designed. Several give a property count, one rate each (five at most, to stay under Gmail's 102 KB clipping limit) and no "add a property" banner. Missing data never leaves a gap. Field names are assumptions in one config block; the banner rule is a business decision I would confirm.

## How I used AI

Claude Code decoded the `.fig` file, exported the artwork, wrote the HTML and AMPscript, and drove Chrome and Word for render tests. Its first versions looked right in a browser and were wrong in Outlook and in dark mode; every such problem was found by rendering, in the end on my own devices.

> **TODO before sending (Alireza):** add two or three sentences on what you personally checked, changed or disagreed with.

## With another day

A Litmus run for the apps I could not test (Yahoo, Samsung Mail, Outlook on Mac and phones); one source for both builds; a German-length check of the fixed-width Outlook buttons; and an accessibility pass, since two colour pairs fall below WCAG AA contrast.

The long version of every point is in `NOTES.md`.
