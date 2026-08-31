# Corpus sample

The retrieval corpus itself (38,692 DACH-region company profiles, licensed from Startup
Insider GmbH) is proprietary and not redistributed in this repository. To make the shape
of the data concrete, the five real profiles below were hand-picked to span the corpus's
actual length distribution — one at the minimum, one at the median, one at the maximum,
and two in between — using the same word-count field the thesis's own filtering rule
(§3.2: "records with at least 30 words in their description") was computed from.

Each company profile is treated as a single retrievable, citeable chunk: nothing here is
split across multiple chunks, so a citation like `[3]` always names exactly one company.

| Percentile | Words | Company |
|---|---|---|
| Minimum | 30 | Kitchn.io |
| Lower quartile | 36 | Wind Mobility |
| Median | 45 | JM Contactless |
| Upper quartile | 63 | Bauernladen.at |
| Maximum | 416 | Siremix |

---

### Minimum (30 words) — Kitchn.io

> Kitchn.io. Founded in 2019. Company size: 11-50. Startup. Germany, Spain. Berlin,
> Palma. Founders: Martin Kreienbaum, Simon Kreienbaum, Stefan Maier. Marketing, Sales
> and Marketing, Software, Digital Marketing, Marketing Automation, subscription, saas,
> B2B, deep tech. Enabling world-class digital marketing operations through workflow
> automation and monitoring. Kitchn.io is a cloud-based workflow automation tool
> designed for social media marketing, helping businesses automate their performance
> marketing workflows. The company leverages low-code development platforms to enhance
> user productivity and streamline operations.

### Lower quartile (36 words) — Wind Mobility

> Wind Mobility. Founded in 2017. Company size: 51-100. Scaleup. Germany, Spain.
> Barcelona, Berlin. saas, commission, B2C, marketplace & ecommerce, mobile app. Wind
> Mobility was a micro-mobility company that developed an e-scooter rental platform,
> providing convenient, affordable, and eco-friendly short-distance transportation in
> urban areas. Its platform allowed users to unlock and access e-scooters via a
> smartphone application, aiming to reduce traffic, carbon dioxide emissions, and noise.

### Median (45 words) — JM Contactless

> JM Contactless. Founded in 2017. Company size: 1-10. Startup. Switzerland. Liddes,
> Martigny. Media and Entertainment, Information Technology, Events, Event Management.
> JM Contactless provides a workable solution for event cash management. JM Contactless
> is a Swiss company that develops and markets cashless payment solutions primarily for
> event organizers. Their system utilizes connected bracelets as a unique payment
> method, centralizing transactions for a fluid and secure experience.

### Upper quartile (63 words) — Bauernladen.at

> Bauernladen.at. Founded in 2018. Company size: 11-50. Scaleup. Austria. Wien. Financial
> Services, E-Commerce, Commerce and Shopping, Marketplace, Retail, Gift Card.
> Bauernladen.at is an online marketplace for regional products, offering direct
> purchases from local farmers. Bauernladen.at is an Austrian online platform operated by
> "bauernladen.at" B2B GmbH, dedicated to facilitating the direct sale of agricultural
> products from local producers to consumers, restaurateurs, and retailers. The company
> aims to promote regionality, quality, biodiversity, and sustainability by connecting
> over 750 Austrian agricultural businesses with customers, thereby reducing transport
> distances and food waste.

### Maximum (416 words) — Siremix *(truncated for length)*

> Siremix. Founded in 2016. Company size: 1-10. Startup. Germany. Berlin. Founders: Moses
> Wong. Digital Entertainment, Media and Entertainment, Software, Audio, Music, Music and
> Audio, Hardware, Consumer Electronics, deep tech, manufacturing, B2C, marketplace &
> ecommerce, virtual reality. SIREMIX is very disruptive for electronic industry, our
> immersive sound technology changes everything - VR, music, TV, cinema, car, mobile...
> Siremix GmbH, founded in Berlin in 2016, is an audio technology company focused on
> revolutionizing sound experiences. They develop products using their patented Endpoint
> Mixing® technology to provide high-quality, immersive audio comparable to high-end
> systems at an affordable price. [...] *(continues for 416 words total, covering
> mission/vision, product line, target customer benefits, and a product roadmap — the
> longest profile in the corpus, roughly 14× the length of the shortest.)*

---

This is exactly the length spread §3.2 of the thesis describes (30–416 words, median 45,
mean 53) — most profiles cluster tightly around the short end, with a long tail of
heavily-enriched entries like Siremix's.
