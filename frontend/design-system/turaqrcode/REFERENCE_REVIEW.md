# QRStuff and Bitly feature review

Reviewed 29 October 2026. References inform features and workflow; TuraQRcode retains its own branding, blue palette, copy, and components.

## Evidence

- [QRStuff public generator](https://www.qrstuff.com/): Firecrawl extracted content, links, and a full-page screenshot. Chrome DevTools MCP independently opened the page, captured its accessible snapshot and screenshot. The observed workflow separates content type, destination, styling, and setup; static/dynamic options, colors, logos, and export formats are prominent.
- [Bitly public product page](https://bitly.com/pages/home/cp): Firecrawl captured the page and screenshot. It presents shortening, QR codes, analytics, branded links, and campaign tagging as distinct product workflows. Chrome DevTools MCP navigation timed out; the complete Firecrawl capture supplied the public-page evidence.
- Chrome DevTools MCP also captured the updated TuraQRcode home and barcode pages at desktop width. Playwright captures the finished desktop/mobile screens and verifies the product workflows.

Full captures stay in ignored `backend/.local/research/`; credentials and downloaded third-party content are not published to Git. Research tools are separate from product runtime dependencies. No private competitor dashboard was accessed and no competitor account was created.

## Implemented decisions

| Observed need | TuraQRcode implementation |
|---|---|
| Immediately understandable creation flow | Content/design/settings tabs, live preview, clearer dedicated barcode and short-link pages |
| More recognizable branded symbols | Seven module patterns, three corner styles, separate corner color, four presets, logo embedding, custom frame labels and border/outline options |
| Reliable color choices | Dark color suggestions, compatible light backgrounds, automatic correction, visible contrast ratio, server-side contrast checks |
| Purpose-built link management | Short-link list/creator, aliases, campaign-tag builder, expiry, access passwords, mobile destinations, activity reports |
| Organized campaigns | Default project for every account, backfilled assignments, explicit project selection, safe project deletion |
| Flexible contact-card branding | Any custom color, automatic text contrast, matching public profile, independent scan-safe QR color |
| Linear barcode workflow requested by the user | Code 128, Code 39, EAN-13, EAN-8, UPC-A; validation, retail check digits, captions, exports, saved management |

These are implemented product capabilities, not a claim of complete parity with either reference. Competitor billing, AI generation, hosted file/media uploads, link-in-bio pages, GS1/digital product passports, integrations, and self-service custom domains remain outside this release. Those features require separate product and operational decisions.

## Reliability references

- [MDN: CSP form-action](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/form-action) explains browser differences around redirects following form submission. The fix permits validated HTTP(S) destinations for the public password page and verifies actual browser navigation.
- [python-barcode supported formats](https://python-barcode.readthedocs.io/en/stable/supported-formats.html) documents the linear barcode formats and checksum behavior. Generated PNGs are independently decoded with ZXing during automated tests.
- [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) supplied the local stdio browser tools used for page captures. A private Node 22 runtime was installed for this research tool because the workspace's Node 22.11 predates its minimum version; the project applications continue to build with the existing runtime.
