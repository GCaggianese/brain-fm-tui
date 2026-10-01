# brain-fm-tui

A terminal interface for Brain.fm, built with [Textual](https://textual.textualize.io/) and powered by [mpv](https://mpv.io/).

![brain-fm-tui running on the Focus tab with Deep Work selected, ADHD mode enabled, and High neural effect](docs/screenshot.png)

> [!IMPORTANT]
> `brain-fm-tui` is an independent project. It is not affiliated with, endorsed by, or maintained by Brain.fm.
>
> Brain.fm is a trademark of its respective owner. The project uses the same private API as the Brain.fm website, which may change without notice.

## Requirements

- Python 3.12 or newer
- [mpv](https://mpv.io/) on your `PATH`
- [`playerctl`](https://github.com/altdesktop/playerctl) *(optional)* for media keys and MPRIS control

`mpv` handles audio playback. Without it, the application can still load activities, but playback will fail.

## Installation

Clone the repository:

```sh
git clone https://github.com/GCaggianese/brain-fm-tui
cd brain-fm-tui
```

### Using uv

```sh
uv sync
uv run brain-fm-tui --setup
uv run brain-fm-tui
```

Run the tests with:

```sh
uv run pytest
```

### Using pip

```sh
pip install .
brain-fm-tui --setup
brain-fm-tui
```

## Authentication

`brain-fm-tui` uses the `token` cookie from an existing Brain.fm browser session.

To get it:

1. Sign in to Brain.fm.
2. Open Developer Tools → **Network**.
3. Reload the page.
4. Open the main document request.
5. Find the `token` cookie and copy its value.

Then run:

```sh
brain-fm-tui --setup
```

Paste the token when prompted and press Enter. Input is hidden while typing.

The token is stored at:

```text
~/.local/share/brain-fm-tui/session
```

Invalid tokens are rejected before anything is saved.

Brain.fm tokens are short-lived. When yours expires, copy a new one and run `--setup` again.

`Ctrl+R` reloads the token from disk. It does not obtain a new one.

## Controls

Use `Tab` and `Shift+Tab` to move between Focus, Relax, Sleep, and Meditate. Each tab shows the activities available for that category.

| Key | Action |
| --- | --- |
| `Enter` | Play selected activity |
| `Space` | Pause / resume |
| `n` | Next track |
| `a` | Toggle ADHD mode |
| `1` | Toggle Low neural effect |
| `2` | Toggle Medium neural effect |
| `3` | Toggle High neural effect |
| `Ctrl+R` | Reload session token |
| `Ctrl+P` | Open Textual command palette |
| `q` | Quit |

The track information above the activity list comes from the track returned by Brain.fm and includes its title, category, activity, genre, length, and tempo.

## Neural effect

The row below the current track shows the neural-effect mix for the selected category.

Low, Medium, and High can be toggled independently. A filled dot means enabled.

ADHD mode corresponds to **High only**. Enabling Low or Medium while ADHD mode is active disables ADHD mode because the mix is no longer exclusively High.

The setting is saved per category using the same account preference as the Brain.fm website. Focus, Sleep, Relax, and Meditate can therefore each have different mixes.

Changing the mix for the category currently playing restarts its session so the new setting takes effect.

## playerctl

`brain-fm-tui` exposes an MPRIS service, so it can be controlled with `playerctl`:

```sh
playerctl play
playerctl pause
playerctl next
playerctl volume 0.5
```

Both `playerctl next` and the `n` key advance through the queue returned by Brain.fm.
When a track ends, the next queued track starts automatically.

The default MPRIS name is:

```text
brainfm
```

If that name is already in use, the active name is shown in the footer.

## License

Apache-2.0. See [LICENSE](LICENSE).
