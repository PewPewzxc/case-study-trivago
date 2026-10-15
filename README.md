# trivago Rate Connect onboarding email

Case study for the Email Development & Marketing Automation internship: a responsive HTML email built from the supplied Figma file, tested for Outlook, Gmail and Apple Mail, with an AMPscript version for Salesforce Marketing Cloud.

Start with [WRITEUP.md](WRITEUP.md) for the approach, what broke, and how AI was used.

## What is here

| Path | Purpose |
| --- | --- |
| `email.html` | The email (Parts 1 and 2). Placeholders are left as drawn in the design, so it renders in any sending tool. |
| `email-ampscript.html` | The same markup with AMPscript (bonus). All logic is in one block at the top of the file. |
| `previews/` | `email.html` with sample data: what the AMPscript produces for a single-property and a multi-property hotelier. |
| `images/` | PNG assets exported from the Figma file at 4x (logos, avatar, icons, the three number circles, and the "Add a property" label for Outlook), plus `bg-white.png`, a tiny background that keeps the header white in dark mode. |
| `screenshots/` | Design vs build vs Outlook engine, mobile widths, the multi-property case, the VML circle test, and the email in real inboxes (Gmail on the web, classic and new Outlook on Windows, Apple Mail and the Gmail app on iPhone). |
| `tests/` | The dark-mode test sheet (`dark-mode-variants.html`, not part of the email), its results and lessons (`RESULTS.md`), and the 51 screenshots from nine app setups. |
| `tools/preflight.py` | Checks run before every test send. |
| `tools/send_test.py` | Sends a file to real inboxes over SMTP, byte for byte. |

## Check it

```bash
python tools/preflight.py email.html email-ampscript.html
```

The script fails on: HTML comments inside Outlook conditional blocks, unbalanced tables or AMPscript, images without `alt` or dimensions, non-ASCII characters, a message over Gmail's 102 KB clipping limit, a stylesheet Gmail would drop, and personalisation syntax inside HTML comments. It warns when an image is not an absolute `https` URL.

## Send a test

```bash
python tools/send_test.py email.html you@gmail.com you@outlook.com
```

## Data the AMPscript expects

These names are assumptions. They are set in the config block at the top of `email-ampscript.html`.

| Where | Field | Use |
| --- | --- | --- |
| Sendable data extension | `hotelier_id` | Key for the property lookup |
| | `hotelier_name` | Greeting. Empty gives "Hello," |
| | `property_name`, `commission_rate` | Fallback when the lookup returns nothing |
| `RateConnect_Properties` | `hotelier_id`, `property_name`, `commission_rate` | One row per property on Rate Connect |

| Properties found | Intro | Tip 2 | "Add a property" banner |
| --- | --- | --- | --- |
| 1 | "Now that *Hotel X* is live" | "Current rate: 12%" | Shown |
| 2 or more | "Now that your *N* properties are live" | One line per property, five at most, then "+ N more" | Hidden |
| None, no fallback | "Now that your property is live" | Rate line left out | Shown |

## Editing notes

- The two HTML files share their markup. A change to one must be made in the other.
- Never put an HTML comment inside an `<!--[if mso]>` block. It ends the block early for every other client.
- The Outlook buttons are VML shapes with a fixed width. "View your campaign" has live text: if it changes or is translated, update the `width` on its `v:roundrect`. "Add a property" has an image label in Outlook (`images/label-add-a-property.png`): a new wording needs a new label image. Everywhere else it is live text.
- The number circles are images (`images/circle-N.png`) except in classic Outlook, which draws them in VML. A new tip needs a new circle image and a new VML number.
- Dark mode: never put a recoloured thing (background colour, text) next to one that is never recoloured (image, VML shape). `tests/RESULTS.md` explains why.
- Link targets are placeholders. The Figma file carries no URLs.
- The images are served from this repository: `https://raw.githubusercontent.com/PewPewzxc/case-study-trivago/main/images/`. If they move, change every address that starts with it in each HTML file: every `src` address and, in the header, the `background` attribute and `background-image`. `tools/send_test.py` refuses to send while any of them does not load.
