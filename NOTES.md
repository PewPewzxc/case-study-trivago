# Rate Connect onboarding email: build notes

The long version of `WRITEUP.md`: every bug in one table, every deviation from the design, and the full testing story. The dark-mode tests themselves are in `tests/RESULTS.md`.

Alireza Pakseresht Koubijari · Email Development & Marketing Automation intern case study · October 2026

## Approach

The Figma file was treated as data rather than a picture. Every size, colour, padding and text style of the Desktop (700px) and Mobile (300px) frames went into a spec first, and the email was built to those numbers. At 700px the build is 1,256px tall, the same as the Figma frame.

- **Structure.** One fluid table, capped at 700px, with eight section rows. All visual styling is inline. The stylesheet holds only resets and one media query (600px), so a client that drops it still shows a fluid version of the desktop layout instead of a broken one.
- **Outlook on Windows.** It renders with Word, so it gets a fixed-width wrapper table, VML shapes for the rounded main button and the three number circles, VML panels that hold the header and footer colours in dark mode, and a pinned sans-serif font. Every other app gets the circles as images, which phones cannot stretch and dark modes cannot recolour. Everything Outlook-specific sits in conditional comments.
- **Two files.** `email.html` keeps the design's placeholders and renders in any sending tool. `email-ampscript.html` is the same markup with AMPscript. `previews/` shows what the AMPscript produces for a single-property and a multi-property hotelier.

## What broke and what changed

| What broke | Cause | Fix |
| --- | --- | --- |
| Outlook: digits clipped inside the number circles | VML text boxes have a default inset that pushed the digit down | Explicit zero-inset text box. Six variants were rendered to pick one (`screenshots/04`) |
| Outlook: the two footer icons were cropped | Outlook crops inline images to an exact line-height | Icon and label moved into separate table cells |
| Outlook: grey hairline around the header logo | Transparent PNG edges resampled without respecting alpha | Recolouring the transparent pixels did not fix it, so the logo is now an opaque PNG |
| Support avatar: round edge cut flat, and faint light seams along its outlines | An outline set to sit inside the shape was exported at full width; each touching shape was smoothed separately | All images re-exported at 16x without per-shape smoothing, then averaged down to 4x. Against Figma's own export: 4 of 71,824 pixels differ noticeably |
| Gmail app on iPhone, dark mode: footer logo vanished, button text turned dark (`screenshots/13`, `14`) | Gmail inverted every colour, dark backgrounds included, but never images | The email now declares itself `light only`, which the Gmail apps honour since October 2026, so they leave it alone. The earlier fixes stay as a fallback: header and button hold their colour with a background image or gradient, and two blend-mode layers keep their text white (Rémi Parmentier's technique) |
| Classic Outlook, dark mode: "Add a property" text vanished; button and circle text turned dark (`25`, `26`) | Classic Outlook recolours text but not VML shapes | The text on VML uses Outlook's gradient text trick and stays white. "Add a property" is a rounded VML button whose label is an image exported from Figma; Outlook recolours neither. Picked after four variants in one test send |
| Both Outlooks, dark mode: header logo in a white box (`15`, `27`) | The header colour is recoloured, the white logo image is not | A gradient (Gmail), a tiny white background image (new Outlook) and a white VML panel (classic Outlook), layered so any one alone works. My first fix, a `data-ogsb` rule, did nothing and was removed. One test failed only because the new image was not uploaded yet, so `tools/send_test.py` now refuses to send when an image does not load |
| Gmail on Android: layout squeezed (once, in dark mode); circles stretched into ovals; the "Add a property" label spilled out of its button | That time Gmail dropped the stylesheet; the phone's larger text setting grows text but not fixed-size boxes | The circles are images exported from Figma (classic Outlook keeps VML circles); the button has a minimum width instead of a fixed one; the support links stack by themselves |
| Footer in dark mode: keeping it navy left dark text on navy in the Gmail app with a non-Google account; my fix, an outline on the logo, changed the brand | That app drops the stylesheet, so text fixes never run there; and the logo is not mine to alter | The plain logo is back and the outline is gone. The footer stays navy everywhere: the Gmail apps leave it alone ("light only"), classic Outlook holds it with a VML panel, new Outlook with a tiny navy background image |
| New Outlook: "Add a property" dropped below the text | Its reading pane (about 650px) was narrower than the width where my inline-block banner stacked | The banner is a table again, side by side in any desktop pane |
| Horizontal overflow at 320px when the stylesheet is ignored | `white-space: nowrap` on the footer links made that row wider than the screen | Removed; the links stack through the media query instead |
| Mobile headline broke in the wrong place | The Figma text holds an invisible line-separator character | Mobile-only line break after "from" |
| An Outlook block ended early for every other client | An HTML comment inside an `[if mso]` block | Removed, and added as a rule to the pre-flight script |

## Where the build leaves the design, and why

- **Font.** SF Pro cannot be served to email clients, so the stack falls back to each platform's system font (SF on Apple, Segoe UI on Windows, Roboto on Android).
- **Problems in the Figma file itself.** Going through the file in Figma, I found three things I assumed were not intended, and corrected them in the build instead of copying them. Checking the logo turned up a fourth.
    - On mobile, the banner sentence under "Got more than one property?" is set to grow sideways instead of wrapping, so it runs out of the frame. The build wraps and centres it.
    - On mobile, the Rate Connect logo sits off-centre, touching the right edge. The build centres it.
    - The small trivago icon in the footer is a 15px circle inside a 14px frame that clips it. The build shows the whole circle.
    - The logo component is 254px wide but its artwork is only 228px, so even a centred box shows the logo 13px left of centre. The build's logo image is cut to the artwork.
- **Support links on mobile.** The design puts them in a full-width row under the avatar. Matching that needs duplicated hidden content or floats, so the build keeps one structure and stacks them beside the avatar.
- **Colour.** The hero subtitle is black at 70% opacity. Classic Outlook ignores `rgba()`, so it is flattened to `#454a4d`.
- **Width.** The design is 700px, wider than the usual 600px. It is kept as drawn. The cost: classic Outlook gets a fixed 700px table and will not shrink it for a narrower reading pane.
- **Dark mode.** The design is light only, and the email says so with `color-scheme: light only`. Apple Mail and Gmail on the web always respected it; the Gmail apps do since October 2026. Classic and new Outlook ignore it, so the email pins its colours there: every dark-mode bug had one cause, something the app recolours (a background colour, text) next to something it never recolours (an image, a VML shape). The fixes were picked from a test sheet sent to nine app setups (`tests/RESULTS.md`). Known leftovers: new Outlook still recolours the light sections (hero, banner, body) in dark mode, which stays readable; classic Outlook shows the footer links white.
- **Footer logo.** The plain trivago logo, never altered. An earlier build gave it a navy outline so it stayed readable where apps turned the footer light; that changed the brand asset, so it was removed. The footer now stays navy in every app tested, so the plain logo always sits on its own colour.

## Testing

Done: Chrome at 700, 600, 375, 320 and 300px; Word's HTML engine, which is what classic Outlook renders with; a copy with the stylesheet removed; and `tools/preflight.py`, which was verified against seven deliberately broken files.

Real inboxes: I sent the email to my own accounts with `tools/send_test.py`, so it arrived exactly as written. Light mode was correct in Gmail on the web, the Gmail app, Apple Mail, and classic and new Outlook (`screenshots/05` to `38`). Dark mode broke in the Gmail app and both Outlooks. To fix it I sent one test sheet, `tests/dark-mode-variants.html`, with three or four candidate fixes per problem, and checked it in nine setups: Gmail on the web, the Gmail app on iPhone and on Android, the Gmail app with an Outlook account, Apple Mail, classic and new Outlook, and Outlook on the web. The results and lessons are in `tests/RESULTS.md`, the 51 screenshots in `tests/screenshots/`. The final build uses the winners. Two more rounds in real inboxes found Android and new Outlook problems, a missing upload and the logo outline; all are fixed (`tests/RESULTS.md`, rounds 3 and 4). In Word's engine, classic Outlook differs from the version confirmed in dark and light only in the rounded "Add a property" button.

On 15 October the final build was checked in every one of those apps, in light and dark mode, and looked as designed everywhere. The only remaining difference is new Outlook recolouring the light sections in dark mode, which stays readable.

## AMPscript (written, not executed)

The script reads the hotelier from the sendable data extension and looks up their properties in a second one. One property gives the email as designed. Several give a property count in the intro, one rate per property (capped at five so a large portfolio cannot push the message past Gmail's 102 KB clipping limit), and no "add a property" banner. Missing data never leaves a gap: no name gives "Hello,", no rate removes the line. Field and table names are my assumptions and sit in one config block. Whether the banner should show for single-property or multi-property accounts is a business rule I would confirm; it is one line to flip.

## How I used AI

I worked in Claude Code. I gave it the brief and the Figma file and asked it to do the task, document how, and teach me the method. It decoded the `.fig` file into a spec, exported the vector artwork to PNG, wrote the HTML and AMPscript, and drove Chrome and Word for the render tests.

What I would stress is that its first version looked correct in a browser and was wrong in Outlook in three places, and its first dark-mode fixes were called done before they had been seen working. None of those were found by reading the code; all were found by rendering it, in the end in real inboxes on my own devices. It also guessed trivago's Business Studio address from memory and got it wrong until a search corrected it. The decisions under "Where the build leaves the design" and the banner rule are the calls I would expect to be challenged on.


## With another day

- A full client matrix in Litmus or Email on Acid. Yahoo, Samsung Mail and Outlook on Mac and phones were not tested.
- One source for both builds (MJML or Marketing Cloud content blocks) so they cannot drift apart.
- A localisation pass with long German strings: the Outlook buttons have a fixed width and need checking per language.
- Confirm the data model and the banner rule with the team, then run the AMPscript in a real preview.
- An accessibility pass. Two colour pairs in the design are below the WCAG AA contrast ratio of 4.5:1 for small text: the grey `#8d8d8b` links on white (3.3:1) and white on the `#0088d9` button (3.8:1). The build keeps the design; I would raise it with the designer.
