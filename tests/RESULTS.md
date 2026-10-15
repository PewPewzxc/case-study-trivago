# Dark-mode test results

On 14 and 15 October 2026, `dark-mode-variants.html` was sent with `tools/send_test.py` and opened in nine app setups, in light and dark mode. Each numbered row of the sheet is one candidate fix for the same problem. The 51 screenshots are in `screenshots/` (addresses blurred). This file records what each app did, which fix won, and what to do differently next time.

## How each app treats dark mode

Everything below follows from this table.

| App | What its dark mode does to an email |
| --- | --- |
| Apple Mail (iPhone) | Nothing. It respects the email's "light only" setting. |
| Gmail on the web | Nothing. Its dark theme only darkens Gmail around the email. |
| Gmail app, iPhone, Google account | Full inversion: light backgrounds turn dark, dark backgrounds turn light, text is flipped to match. Images are never changed. Reads the email's stylesheet, so Gmail-only fixes run. |
| Gmail app, iPhone, non-Google account (an Outlook account added to the Gmail app) | The same inversion, but it **drops the stylesheet**. Only inline styles survive, so any fix that lives in a CSS class does not run. |
| Gmail app, Android, Google account | Partial: light backgrounds turn dark; dark backgrounds and white text stay. Background images do not keep the header white. |
| Classic Outlook (Windows) | Full inversion of every HTML colour, text included. VML shapes and images are never changed, but text drawn on a VML shape is. |
| New Outlook (Windows) | Partial: light backgrounds turn dark, navy turns slate grey, light text stays light. Honours background images; ignores CSS gradients and the `data-ogsb` rule. |
| Outlook on the web | Only light mode was checked: correct. |

## Results row by row

✓ = looks as designed or reads correctly; ✗ = broken or unreadable.

**Section 1: buttons and circles.** Only classic Outlook draws these rows differently; every other app showed the same HTML version in all four rows.

| Row | Classic Outlook, light | Classic Outlook, dark | Verdict |
| --- | --- | --- | --- |
| 1A today: VML shape, plain text colour | ✓ | ✗ button and circle text dark; "Add a property" white on white | Broken |
| 1B VML shape, `mso-color-alt` on the text | ✗ button and circle text black | ✓ white text; ✗ "Add a property" still invisible | Breaks light mode |
| 1C VML shape, gradient text trick | ✓ white text; ✗ "Add a property" invisible | ✓ all readable | **Winner for white text** (main button, circles) |
| 1D No VML, plain table cells | ✓ square corners | ✓ recoloured together, readable | **Winner for "Add a property"** |

**Section 2: header logo** (dark mode).

| Row | Classic Outlook | New Outlook | Gmail iPhone | Gmail iPhone, non-Google | Gmail Android |
| --- | --- | --- | --- | --- | --- |
| 2A today: colour + gradient | ✗ boxed | ✗ boxed | ✓ | ✓ | ✗ boxed |
| 2B + white VML panel, wider `data-ogsb` rules | ✓ | ✗ boxed | ✓ | ✓ | ✗ boxed |
| 2C white background image, no colour | ✗ boxed, and grey in light mode | ✓ | ✓ | ✓ | ✗ boxed |

Winner: colour + white background image (2C) + white VML panel (2B). Nothing tested kept it white on Android.

**Section 3: footer** (dark mode).

| Row | Classic Outlook | New Outlook | Gmail iPhone | Gmail iPhone, non-Google | Gmail Android |
| --- | --- | --- | --- | --- | --- |
| 3A today: outlined logo, footer may recolour | light footer, outlined logo, readable | slate footer, outline shows, readable | light footer, outlined logo, readable | the same, readable | ✓ navy |
| 3B plain logo, navy held by gradient + VML, text tricks | ✓ navy; ✗ links dark teal | slate, gradient ignored | navy, white text; links turn peach | ✗ **dark text on navy, unreadable** | ✓ |
| 3C plain logo, navy held by background image + VML, `mso-color-alt` | ✓ navy, links white | ✓ exactly as designed | navy, white text; links turn peach | ✗ **dark text on navy, unreadable** | ✓ |

Winner: 3A for every app, plus 3C's navy VML panel and `mso-color-alt`, which only classic Outlook reads.

## What went into the final email

- **Main button and circles:** VML shapes with the gradient text trick (`.mso-keep-white`, 1C) for classic Outlook. Everyone else: the button keeps its Gmail fix (gradient + blend-mode layers); the circles became images in round 3.
- **"Add a property":** in round 3 a plain table cell in Outlook (1D); in round 4 a rounded VML button with an image label.
- **Header:** white colour + gradient on the outer cell (2A), tiny white background image on the inner cell (2C), white VML panel (2B).
- **Footer:** the plain white logo (the outline from 3A was removed in round 4: the logo is never altered), plus a navy VML panel and `mso-color-alt` for classic Outlook.
- **Support links:** inline blocks that stack by themselves (round 3). The banner went back to its table in round 4.
- **`color-scheme: light only`** (round 4): the Gmail apps stop recolouring the email.
- **Removed:** the `[data-ogsb] .keep-white` rule. It did nothing.

## What is still not perfect, and why it is accepted

- **The Gmail apps:** with "light only" they should not recolour the email at all (round 4, to be confirmed in a real send). Before that, Gmail on Android boxed the header logo in dark mode and once dropped the stylesheet (wider margins, numbers beside the text, the legal address as a blue link). The fixes from rounds 1 to 3 stay in the email as a fallback for app versions that do not honour "light only".
- **Gmail app with a non-Google account:** not yet known whether it honours "light only". If it does not, the main button's text turns dark on blue (readable) and the plain footer logo can disappear on a footer it turns light.
- **New Outlook:** in dark mode it still recolours the light sections (hero, banner, body) to dark tones and turns their text light. That is readable and normal. Holding those sections light is not safe: new Outlook would still turn the dark text light, giving light text on a light background.
- **Classic Outlook:** footer links are white instead of light blue. If pictures are blocked, "Add a property" shows its alt text instead of the label image.
- **Not tested:** Yahoo, Samsung Mail, Outlook on Mac and phones, and Outlook on the web in dark mode.

## Round 3: the finished email in real inboxes (15 October, night)

| App | What it showed | Cause | Change |
| --- | --- | --- | --- |
| Classic Outlook | Correct in light and dark | | None |
| New Outlook, dark | Header logo in a white box | `images/bg-white.png` was not uploaded yet, so the background image did not load | Uploaded. `tools/send_test.py` now refuses to send when any image does not load |
| Gmail app, iPhone, dark | Header logo in a white box; circles correct | Same missing image, and the gradient that used to keep the header white had been replaced by it | The gradient is back on the outer header cell, the image on the inner cell: either one alone keeps it white |
| Gmail app, Android, light | Phone layout, correct | | None |
| Gmail app, Android, dark | Desktop layout squeezed onto the phone: banner text in a narrow column, links wrapping; the legal address turned into a blue link | Gmail on Android drops the stylesheet in dark mode, so the media query and the Gmail-only rules are gone | Banner and support links are now inline blocks that stack by themselves when there is no room (Outlook keeps its tables through ghost tables) |
| Gmail app, Android, both modes | Number circles stretched into ovals | The phone's larger text setting grows the text but not the fixed 32px circle around it | The circles are images now (`images/circle-1.png` to `3`), exported from Figma; Outlook keeps its VML circles |

After these changes, classic Outlook renders pixel-identical to the version confirmed above (checked through Word's engine), and Chrome is identical except the circles (now images) and the "Add a property" button, which is now exactly the design's 124px wide instead of 129px.

## Round 4: asking the apps instead of fighting them (15 October, early morning)

| App | What it showed | Cause | Change |
| --- | --- | --- | --- |
| Classic Outlook, light | "Add a property" with square corners | The plain table cell from row 1D | A rounded VML button again, with the label as an image exported from Figma: Outlook's dark mode never recolours VML shapes or images, so it stays white with black text in both modes |
| New Outlook (pane about 650px wide) | "Add a property" below the text, left-aligned | The round-3 inline blocks stack below 700px | Banner back to the table layout, which stays side by side in any desktop pane |
| Gmail app, Android, dark | "Add a property" label spilling out of the button | The button had a fixed 124px width and the phone enlarges text | `min-width` plus padding: 124px at normal text size, wider when the text grows |
| Gmail app, Android, dark | Phone layout this time, circles round | | None |
| Every app that recolours the footer | The outlined logo showed its outline | The outline was a change to the trivago logo; the brand rule is that the logo is never altered | Removed. The footer uses the plain white logo (`images/logo-trivago-footer.png`) |

The key change of this round is one word. The email always said `<meta name="color-scheme" content="light">`. Since October 2026 the Gmail apps on iPhone and Android honour `content="light only"` and then stop recolouring the email altogether (Dyspatch, 8 October 2026). With that, the footer stays navy with the plain logo in the Gmail apps, as in Apple Mail and Gmail on the web. Classic Outlook holds it navy with its VML panel. New Outlook ignores the setting and turns the footer slate grey, where the plain white logo still reads. Holding navy there with a background image was rejected: any app that still inverts the text would put dark legal text on navy.

Not yet confirmed in a real inbox: whether the Gmail app with a non-Google account also honours "light only".

## Round 5: the footer in new Outlook (15 October, morning)

With "light only" in place, the email looked as designed in every app tested except new Outlook, which turned the navy footer slate grey. Holding it navy with a background image (row 3C) had been rejected because an app that still recolours text would put dark legal text on that navy. That risk was the Gmail apps, and they now leave the email alone. So the footer got row 3C's markup: a tiny navy background image (`images/bg-navy.png`) plus the blend-mode text layers as a backstop for Gmail versions that still invert. Light mode is pixel-identical in Chrome and Word's engine.

## Lessons for next time

1. **Know each app's dark mode before fixing anything.** There are four behaviours: none, partial, full inversion, and full inversion without a stylesheet. A fix only makes sense against the behaviour it targets.
2. **The one rule.** Never put something an app recolours (a background colour, text) next to something it never recolours (an image, a VML shape, a background image). Every bug in this email broke that rule.
3. **Only protect a background if you can protect its text too, in every app.** Rows 3B and 3C held the footer navy and were close to perfect in four apps. In the fifth they made the legal text unreadable, which is worse than doing nothing. If text cannot be pinned, let the background and text recolour together.
4. **Inline styles survive; classes may not.** Some apps drop the whole stylesheet. Before relying on a class-based fix, ask what that element looks like without it.
5. **Test fixes side by side, in light and dark, in every app.** Rows 1B and 1C each fixed dark mode and broke light mode. Only a side-by-side sheet shows that in one send.
6. **A test sheet is not the real email.** Squashed buttons and circles on narrow phones came from the sheet's own layout. The final email still needs its own check.
7. **Test sends from a personal account land in spam.** In spam, images are blocked: check that alt text reads well. Real inbox placement depends on trivago's sending domain (SPF, DKIM), not on the HTML.
8. **Do not let the phone layout depend on the stylesheet.** Gmail on Android drops it in dark mode, and the Gmail app with a non-Google account always does. Anything that must stack on a phone should stack by itself (inline blocks), with the media query only polishing it.
9. **Text size is the reader's choice; boxes around text must allow for it.** A fixed-size circle around live text turns into an oval when a phone enlarges text. Either let the box grow evenly or use an image.
10. **Keep the old fallback when adding a new technique.** Swapping the header gradient for a background image removed a fix that already worked, and the header broke the moment the image was missing.
11. **A missing file looks exactly like an app bug.** Check that every image loads before testing; `tools/send_test.py` now does this itself.
12. **First ask whether the apps can simply be told not to recolour.** One meta tag (`color-scheme: light only`) now switches off the Gmail apps' dark mode. It would have saved most of rounds 1 to 3 in the Gmail apps. Read the current documentation before engineering around a behaviour.
13. **Brand assets are not yours to change.** A fix that alters a logo is not a fix. Hold the colours around the logo instead, or accept a recoloured background.
14. **Check layouts at real reading-pane widths, not only at 700 and 375.** New Outlook's pane was about 650px, exactly where the inline-block banner stacked.
