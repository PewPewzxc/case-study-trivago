# Dark-mode test results

`dark-mode-variants.html` was sent with `tools/send_test.py` and opened in eight app setups (Gmail on the web, the Gmail app on iPhone (with a Google account and with an Outlook account), the Gmail app on Android, Apple Mail, classic Outlook, new Outlook and Outlook on the web), in light and dark mode. Each numbered row of the sheet is one candidate fix for the same problem. The 51 screenshots are in `tests/screenshots/` (addresses blurred). This file records what each app did, which fix won, and what to do differently next time. Rounds 1 and 2 were the first two real-inbox sends of the email (top-level `screenshots/05` to `18`, then `19` to `38` after the first fixes). Then came this test sheet, then rounds 3 to 7 below.

## How each app treats dark mode

Everything below follows from this table. It shows how the apps behaved before round 4, when the email still said `light`. Since round 4 it says `light only`, and the Gmail app leaves it alone for Google accounts. With a non-Google account it doesn't (round 7).

| App | What its dark mode does to an email |
| --- | --- |
| Apple Mail (iPhone) | Nothing. It respects the email's light setting. |
| Gmail on the web | Nothing. Its dark theme only darkens Gmail around the email. |
| Gmail app, iPhone, Google account | Full inversion: light backgrounds turn dark, dark backgrounds turn light, text is flipped to match. Images are never changed. Reads the email's stylesheet, so Gmail-only fixes run. |
| Gmail app, iPhone, non-Google account (an Outlook account added to the Gmail app) | The same inversion, but it **drops the stylesheet**. Only inline styles survive, so any fix that lives in a CSS class does not run. |
| Gmail app, Android, Google account | Partial: light backgrounds turn dark; dark backgrounds and white text stay. Background images do not keep the header white. |
| Classic Outlook (Windows) | Full inversion of every HTML color, text included. VML shapes and images are never changed, but text drawn on a VML shape is. |
| New Outlook (Windows) | Partial: light backgrounds turn dark, navy turns slate gray, light text stays light. Honors background images; ignores CSS gradients and the `data-ogsb` rule. |
| Outlook on the web | Only light mode was checked: correct. |

## Results row by row

✓ = looks as designed or reads correctly; ✗ = broken or unreadable.

**Section 1: buttons and circles.** Only classic Outlook draws these rows differently; every other app showed the same HTML version in all four rows.

| Row | Classic Outlook, light | Classic Outlook, dark | Verdict |
| --- | --- | --- | --- |
| 1A today: VML shape, plain text color | ✓ | ✗ button and circle text dark; "Add a property" white on white | Broken |
| 1B VML shape, `mso-color-alt` on the text | ✗ button and circle text black | ✓ white text; ✗ "Add a property" still invisible | Breaks light mode |
| 1C VML shape, gradient text trick | ✓ white text; ✗ "Add a property" invisible | ✓ all readable | **Winner for white text** (main button, circles) |
| 1D No VML, plain table cells | ✓ square corners | ✓ recolored together, readable | **Winner for "Add a property"** |

**Section 2: header logo** (dark mode).

| Row | Classic Outlook | New Outlook | Gmail iPhone | Gmail iPhone, non-Google | Gmail Android |
| --- | --- | --- | --- | --- | --- |
| 2A today: color + gradient | ✗ boxed | ✗ boxed | ✓ | ✓ | ✗ boxed |
| 2B + white VML panel, wider `data-ogsb` rules | ✓ | ✗ boxed | ✓ | ✓ | ✗ boxed |
| 2C white background image, no color | ✗ boxed, and gray in light mode | ✓ | ✓ | ✓ | ✗ boxed |

Winner: color + gradient on the outer cell (2A), a white background image (2C) and a white VML panel (2B), layered. Nothing tested kept it white on Android.

**Section 3: footer** (dark mode).

| Row | Classic Outlook | New Outlook | Gmail iPhone | Gmail iPhone, non-Google | Gmail Android |
| --- | --- | --- | --- | --- | --- |
| 3A today: outlined logo, footer may recolor | light footer, outlined logo, readable | slate footer, outline shows, readable | light footer, outlined logo, readable | the same, readable | ✓ navy |
| 3B plain logo, navy held by gradient + VML, text tricks | ✓ navy; ✗ links dark teal | slate, gradient ignored | navy, white text; links turn peach | ✗ **dark text on navy, unreadable** | ✓ |
| 3C plain logo, navy held by background image + VML, `mso-color-alt` | ✓ navy, links white | ✓ exactly as designed | navy, white text; links turn peach | ✗ **dark text on navy, unreadable** | ✓ |

Winner: 3A for every app (its logo outline was removed later, in round 4), plus 3C's navy VML panel and `mso-color-alt`, which only classic Outlook reads.

## What went into the final email

- **Main button and circles:** VML shapes with the gradient text trick (`.mso-keep-white`, 1C) for classic Outlook. Everyone else: the button keeps its Gmail fix (gradient + blend-mode layers); the circles became images in round 3.
- **"Add a property":** in round 3 a plain table cell in Outlook (1D); in round 4 a rounded VML button with an image label; finally a plain cell with live text again, square corners on purpose, so every word can be translated.
- **Header:** white color + gradient on the outer cell (2A), tiny white background image on the inner cell (2C), white VML panel (2B).
- **Footer:** the plain white logo (the outline from 3A was removed in round 4: the logo is never altered), plus a navy VML panel and `mso-color-alt` for classic Outlook, a tiny navy background image for new Outlook (round 5), and the Gmail blend-mode layers on the text as a fallback (round 5).
- **Support links:** inline blocks that stack by themselves (round 3). The banner went back to its table in round 4.
- **`color-scheme: light only`** (round 4): the Gmail app stops recoloring the email for Google accounts.
- **Removed:** the `[data-ogsb] .keep-white` rule. It did nothing.

## What is still not perfect, and why it is accepted

- **The Gmail app with a Google account:** with "light only" it no longer recolors the email, confirmed on my phones after round 4. Before that, Gmail on Android boxed the header logo in dark mode and once dropped the stylesheet (wider margins, numbers beside the text, the legal address as a blue link). The fixes from rounds 1 to 3 stay in the email as a fallback for app versions that do not honor "light only".
- **Gmail app with a non-Google account (iPhone): not solved.** It does not respect "light only", and in dark mode the footer's legal text becomes almost unreadable (round 7).
- **New Outlook:** in dark mode it still recolors the light sections (hero, banner, body) to dark tones and turns their text light. That is readable and normal. Holding those sections light is not safe: new Outlook would still turn the dark text light, giving light text on a light background.
- **Classic Outlook:** footer links are white instead of light blue. "Add a property" has square corners there, a deliberate trade for translatable text.
- **Covered by Email on Acid, not on my own devices:** Yahoo, Samsung Mail, Outlook on Mac and on phones, and Outlook on the web in dark mode (round 6). Only T-Online and the Pixel test phones showed problems there.

## Round 3: the finished email in real inboxes

| App | What it showed | Cause | Change |
| --- | --- | --- | --- |
| Classic Outlook | Correct in light and dark | | None |
| New Outlook, dark | Header logo in a white box | `images/bg-white.png` was not uploaded yet, so the background image did not load | Uploaded. `tools/send_test.py` now refuses to send when any image does not load |
| Gmail app, iPhone, dark | Header logo in a white box; circles correct | Same missing image, and the gradient that used to keep the header white had been replaced by it | The gradient is back on the outer header cell, the image on the inner cell: either one alone keeps it white |
| Gmail app, Android, light | Phone layout, correct | | None |
| Gmail app, Android, dark | Desktop layout squeezed onto the phone: banner text in a narrow column, links wrapping; the legal address turned into a blue link | Gmail on Android drops the stylesheet in dark mode, so the media query and the Gmail-only rules are gone | Banner and support links are now inline blocks that stack by themselves when there is no room (Outlook keeps its tables through ghost tables) |
| Gmail app, Android, both modes | Number circles stretched into ovals | The phone's larger text setting grows the text but not the fixed 32px circle around it | The circles are images now (`images/circle-1.png` to `3`), exported from Figma; Outlook keeps its VML circles |

After these changes, classic Outlook renders pixel-identical to the version confirmed above (checked through Word's engine), and Chrome is identical except the circles (now images) and the "Add a property" button, which is now exactly the design's 124px wide instead of 129px.

## Round 4: asking the apps instead of fighting them

| App | What it showed | Cause | Change |
| --- | --- | --- | --- |
| Classic Outlook, light | "Add a property" with square corners | The plain table cell from row 1D | A rounded VML button again, with the label as an image exported from Figma: Outlook's dark mode never recolors VML shapes or images, so it stays white with black text in both modes |
| New Outlook (pane about 650px wide) | "Add a property" below the text, left-aligned | The round-3 inline blocks stack below 700px | Banner back to the table layout, which stays side by side in any desktop pane |
| Gmail app, Android, dark | "Add a property" label spilling out of the button | The button had a fixed 124px width and the phone enlarges text | `min-width` plus padding: 124px at normal text size, wider when the text grows |
| Gmail app, Android, dark | Phone layout this time, circles round | | None |
| Every app that recolors the footer | The outlined logo showed its outline | The outline was a change to the trivago logo; the brand rule is that the logo is never altered | Removed. The footer uses the plain white logo (`images/logo-trivago-footer.png`) |

The key change of this round is one word. The email always said `<meta name="color-scheme" content="light">`. Since a recent update, the Gmail apps on iPhone and Android, with Google accounts, honor `content="light only"` and then stop recoloring the email altogether (reported by Dyspatch). With that, the footer stays navy with the plain logo in the Gmail apps, as in Apple Mail and Gmail on the web. Classic Outlook holds it navy with its VML panel. New Outlook ignores the setting and turns the footer slate gray, where the plain white logo still reads. Holding navy there with a background image was rejected: any app that still inverts the text would put dark legal text on navy.

Later confirmed (round 7): the Gmail app with a non-Google account does not honor "light only".

## Round 5: the footer in new Outlook

With "light only" in place, the email looked as designed in every app tested except new Outlook, which turned the navy footer slate gray. Holding it navy with a background image (row 3C) had been rejected because an app that still recolors text would put dark legal text on that navy. That risk was the Gmail apps. With Google accounts they now leave the email alone. With a non-Google account the risk was real after all (round 7). So the footer got row 3C's tiny navy background image (`images/bg-navy.png`) plus row 3B's blend-mode text layers as a backstop for Gmail versions that still invert. Light mode is pixel-identical in Chrome and Word's engine.

## Round 6: Email on Acid

I ran the finished email through Email on Acid. Everything looked right except two groups:

| App | What it showed | Cause | Change |
| --- | --- | --- | --- |
| T-Online webmail (Chrome, Edge, Firefox on Windows 10) | The number circles 1, 2 and 3 were missing | T-Online deletes everything between `<!--[if !mso]><!-->` and `<!--<![endif]-->`, the wrapper that hides the HTML version of something from classic Outlook. The circle images sit in that wrapper. So do the HTML versions of both buttons, so those were probably missing too | Every wrapper now has a space inside: `<!--[if !mso]><! -->` and `<!-- <![endif]-->`. T-Online leaves that spelling alone (Rémi Parmentier's email-bugs, issue 43). In Chrome and in Word's engine the email renders exactly as before. `tools/preflight.py` now fails on the old spelling. **Confirmed fixed** in a second Email on Acid run |
| Gmail app, Pixel 6 to 10 (Android 12 to 16), dark mode | The footer was an empty white box: logo, text and links all gone. Everything else was fine, and light mode was correct (top-level `screenshots/39`, `40`) | Most likely a bug in Email on Acid's Pixel setup. A real Gmail darkening recolors a footer, it doesn't erase it. It was still there in a second Email on Acid run, but on a real Pixel 8 Pro with Android 17, on my own Android phone and on two other Android devices, the footer is correct. One possible reason is an older Gmail on the test phones that ignores "light only". Chrome's built-in automatic darkening, which Gmail on Android is reported to rely on, keeps the footer navy and readable, so I couldn't reproduce it | None, on purpose. Changing a footer that works on real phones to suit one test setup would risk breaking it. Raised as a question for trivago (which devices and versions to support) |

The real devices were a Pixel 8 Pro with Android 17, my own Android phone and two other Android devices. Their Gmail app versions aren't recorded here. The Android version isn't really what varies here. The Gmail app updates itself through the Play Store, separately from Android, so the Gmail version on the test phone matters more than the Android number.

## Round 7: the Gmail app with an Outlook account

In dark mode, the real email's footer legal text was almost unreadable in the Gmail app on iPhone with an Outlook account: dark text on the navy. This setup ignores "light only" and drops the style block, so the blend layers that keep the text white (a style-block rule) never run, while the navy background image is never recolored.

Test sheet: `tests/footer-variants.html`, sent to that setup.

| Row | Dark mode | Light mode | Verdict |
| --- | --- | --- | --- |
| A. current footer | ✗ legal text almost invisible; links dim | ✓ | The bug |
| B. blend layers written inline, switched off by the style block elsewhere | ✗ text in white boxes | ✗ text in black boxes | Rejected: this setup keeps the background but ignores the blend mode |
| C. legal text `#a3abb8` instead of white | ✓ readable | ✓ readable | Works, but changes the design's white |

Not applied. I left the email as designed and flagged it as an open question. A second sheet with lighter grays (`tests/footer-shades.html`) is prepared but hasn't been sent.

## Lessons for next time

1. **Know each app's dark mode before fixing anything.** There are four behaviors: none, partial, full inversion, and full inversion without a stylesheet. A fix only makes sense against the behavior it targets.
2. **The one rule.** Never put something an app recolors (a background color, text) next to something it never recolors (an image, a VML shape, a background image). Every dark-mode color bug in this email broke that rule.
3. **Only protect a background if you can protect its text too, in every app.** Rows 3B and 3C held the footer navy and were close to perfect in four apps. In the fifth they made the legal text unreadable, which is worse than doing nothing. If text cannot be pinned, let the background and text recolor together. Round 5 still added this for new Outlook, because by then the Gmail apps seemed to leave the email alone. Round 7 showed the risk was real after all, for the Gmail app with a non-Google account.
4. **Inline styles survive; classes may not.** Some apps drop the whole stylesheet. Before relying on a class-based fix, ask what that element looks like without it.
5. **Test fixes side by side, in light and dark, in every app.** Rows 1B and 1C each fixed dark mode and broke light mode. Only a side-by-side sheet shows that in one send.
6. **A test sheet is not the real email.** Squashed buttons and circles on narrow phones came from the sheet's own layout. The final email still needs its own check.
7. **Test sends from a personal account land in spam.** In spam, images are blocked: check that alt text reads well. Real inbox placement depends largely on the sender's domain reputation and authentication (SPF, DKIM), which a personal test account doesn't have.
8. **Do not let the phone layout depend on the stylesheet.** Gmail on Android dropped it once, in dark mode, and the Gmail app with a non-Google account always does. Anything that must stack on a phone should stack by itself (inline blocks), with the media query only polishing it.
9. **Text size is the reader's choice; boxes around text must allow for it.** A fixed-size circle around live text turns into an oval when a phone enlarges text. Either let the box grow evenly or use an image.
10. **Keep the old fallback when adding a new technique.** Swapping the header gradient for a background image removed a fix that already worked, and the header broke the moment the image was missing.
11. **A missing file looks exactly like an app bug.** Check that every image loads before testing; `tools/send_test.py` now does this itself.
12. **First ask whether the apps can simply be told not to recolor.** One meta tag (`color-scheme: light only`) now switches off the Gmail app's dark mode for Google accounts. It would have saved most of rounds 1 to 3 in the Gmail apps. Read the current documentation before engineering around a behavior.
13. **Brand assets are not yours to change.** A fix that alters a logo is not a fix. Hold the colors around the logo instead, or accept a recolored background.
14. **Check layouts at real reading-pane widths, not only at 700 and 375.** New Outlook's pane was about 650px, exactly where the inline-block banner stacked.
15. **A testing service covers apps you don't own.** T-Online, a large German webmail, deletes content that every other app shows. I would never have found it on my own devices.
