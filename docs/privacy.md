# Akane Bot Privacy Policy

_Effective: 22 November 2026 · Last updated: 23 November 2026_

Hi! This page explains, in plain words, what Akane Bot ("Akane", "the bot", "we") does with your information when you use it on Discord.

Akane is run by fenix.er and is open source under the AGPL-3.0 licence. You can always [read the code](https://github.com/infernalsaber/AkaneBot) to see exactly what it does.

**The short version:** Akane keeps very little. It doesn't store your messages, doesn't sell or share your data, and you can ask us to delete anything tied to you at any time.

---

## 1. Messages

Akane can see messages in channels it has access to. It only looks at them for two things:

- to spot when someone is talking to it, meaning a message that starts with its prefix or mentions it
- to spot links from supported sites whose previews don't show properly on Discord (such as MangaPlus or Miyoushe), so it can reply with a proper preview

**Akane does not store, log, or read through your conversations.** Once it has checked a message for a command or a supported link, the message is forgotten.

---

## 2. What Akane stores

### Data you give us through a command

**Your AniList username (optional).** If you link your AniList account, using `-um set <name>` or the "Add username" button, we save:

- your Discord user ID
- the AniList username and AniList user ID you gave us
- when the link was made or last changed

This lets you type `-user` on its own and see your profile without typing your name every time.

If you haven't linked an account, Akane may ask once whether you'd like to. If you pick **"Not now"** or **"Don't ask again"**, we save that choice next to your Discord ID so we don't keep asking.

**Server prefixes.** If a server admin sets custom command prefixes, we save the server's ID and those prefixes. This is about the server, not about any one person.

### Data collected automatically

**Command usage counts.** We keep a running total of how often each command is used (for example, "`anime` has been used 500 times"). **These counts are not linked to any user or server.** They only tell us which features people use.

**Logs.** Akane writes logs so we can fix things when they break. Logs may include error details, such as the link to an image a sauce search failed on. They are small, overwrite themselves as they fill up, and are wiped each time the bot restarts. We only use them to fix bugs.

**Cache.** To be faster and lighter on the websites it uses, Akane briefly saves the replies it gets from them (for example, AniList's reply to an anime search). This cache expires on its own, usually within a day.

### What Akane looks at but doesn't keep

- **Images and videos you ask it to search.** When you use the sauce command, Akane looks at the image or video you point it to. Images are handled in memory and not saved. For videos, it takes one frame to search with and then discards it.
- **Discord profile and server info.** Commands like `userinfo` or `pfp` show public Discord info, such as your avatar, username and join date. Akane holds this in memory while it runs, the same way every Discord bot does, but doesn't save it anywhere.

---

## 3. Why we use it

We use the data above only to:

- run the commands you ask for
- fix the previews of supported links
- remember your preferences (your AniList link, your server's prefixes)
- fix bugs and keep the bot running smoothly
- understand which features are popular

Nothing else. We don't build profiles of people, and we don't use your data for anything you didn't ask for.

### Legal basis (for users in the EU and UK)

Under the GDPR and UK GDPR, we need a legal reason to use your data. Ours are:

| What | Legal basis |
| --- | --- |
| Linked AniList username | **Consent:** you chose to link it, and you can remove it any time with `-um remove` |
| "Not now" / "Don't ask again" choice | **Legitimate interest:** respecting your choice so we don't keep asking |
| Server prefixes | **Legitimate interest:** making the bot work the way the server's admins set it up |
| Logs and cache | **Legitimate interest:** keeping the bot working, fast and bug-free |
| Messages, images and searches | **Legitimate interest:** running the commands you ask for, and fixing the previews of supported links |

Command usage counts aren't about anyone, so they aren't personal data.

---

## 4. Sharing and third parties

**We don't sell, rent or trade your data.**

To answer your commands and fix link previews, Akane asks other services for help. It only sends what each request needs, such as the anime you searched for or the link to an image you want the source of. **It never sends your Discord ID or anything else about you.**

| Service | Used for | What it receives |
| --- | --- | --- |
| [AniList](https://anilist.co), [MyAnimeList](https://myanimelist.net) and [Jikan](https://jikan.moe) | Anime, manga, character and user lookups | Your search, or an AniList username |
| [SauceNAO](https://saucenao.com) and [trace.moe](https://trace.moe) | Finding the source of an image or anime scene | A link to the image or frame |
| [VNDB](https://vndb.org) | Visual novel lookups | Your search |
| [MangaDex](https://mangadex.org) and [ComicK](https://comick.io) | Manga chapters and updates | Series names or IDs |
| [MangaPlus](https://mangaplus.shueisha.co.jp) and [Miyoushe](https://www.miyoushe.com) | Fixing link previews | The chapter, series or post ID from the link |
| [YouTube](https://youtube.com) | Trailers and videos | Your search |
| [Steam](https://store.steampowered.com) and [Hakushin](https://hakush.in) | Game info | Your search |
| [7TV](https://7tv.app) | Finding emotes to add to a server | The emote name or link |

Each of these has its own privacy policy. Akane also runs on Discord, so [Discord's Privacy Policy](https://discord.com/privacy) applies to everything you do there.

---

## 5. Storage and security

Akane's data lives on a private server we manage. Its database isn't open to the internet, and only the bot's developer can access it. No system is perfectly secure, so we can't promise absolute security, but we keep what we store small on purpose so there's very little to lose in the first place.

---

## 6. How long we keep things

| What | How long |
| --- | --- |
| Linked AniList username | Until you remove it |
| "Not now" / "Don't ask again" choice | Until you ask us to delete it |
| Server prefixes | Until a server admin removes them, or you ask us to |
| Command usage counts | Indefinitely (they aren't about anyone) |
| Logs | Until overwritten or the bot restarts, whichever comes first |
| Cache | Usually up to a day |

We don't keep backups right now. If we add them in future, they'll only hold the last 30 days, so anything you delete will be fully gone within 30 days.

---

## 7. Your choices and rights

- **Remove your AniList link any time** with `-um remove`. Your saved username is deleted straight away.
- **Want everything gone?** After `-um remove`, Akane still keeps your Discord ID next to your "don't ask me" choice, so it remembers not to ask again. If you'd like that removed too, contact us and we'll delete every record tied to your Discord ID.
- **Ask what we have.** Contact us and we'll tell you exactly what's stored about you.
- **Server data.** Removing Akane from a server stops it from seeing anything there. A server owner or admin can ask us to delete that server's prefix settings.

If you're in the EU or UK, data protection law also gives you the right to have your data corrected, to get a copy of it, to object to how we use it, and to ask us to limit what we do with it. You can also complain to your local data protection authority, though we'd love the chance to sort things out with you first.

To protect you, we may ask you to confirm the request comes from the account in question (for example, by messaging us from that Discord account). We'll usually reply within a week, and within a month at the very latest.

---

## 8. Age

Akane is meant for people old enough to use Discord under [Discord's Terms of Service](https://discord.com/terms). We don't knowingly collect data from anyone younger than that. If you think a child has given us their information, contact us and we'll delete it.

---

## 9. Self-hosted copies

Akane's code is public, so anyone can run their own copy. This policy only covers the official instance run by fenix.er. If you're using someone else's copy, its operator is responsible for your data and should have their own policy.

---

## 10. Changes to this policy

If we change how Akane handles your data, we'll update this page and the date at the top. For bigger changes, we'll try to let people know through the bot or its support server, [Akane-Bot Land](https://discord.gg/7fr7AfZu4n). Continuing to use Akane after a change means you're okay with the updated policy.

---

## 11. Contact

Questions, worries, or deletion requests? We're happy to help:

- Message **fenix.er** on Discord
- Join the support server, [Akane-Bot Land](https://discord.gg/7fr7AfZu4n)
- Or open an issue on [GitHub](https://github.com/infernalsaber/AkaneBot/issues)

Akane Bot isn't affiliated with or endorsed by Discord Inc.
