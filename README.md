# brain-fm-tui

brain-fm-tui plays a Brain.fm subscription in the terminal. The interface is a Python program written with [Textual](https://textual.textualize.io/). The sound comes out of [mpv](https://mpv.io/). Nothing here opens a browser, and the official desktop app is never started.

![Focus, Deep Work, ADHD on, High neural effect](docs/screenshot.png)

This project has nothing to do with Brain.fm. It is not their software, and they have not endorsed it. Brain.fm is a trademark of its owner. You need your own account and an active subscription. The player calls the same private API the website uses. That API is not a public contract, and it can change or stop answering.

## Requirements

Python 3.12 or newer.

`mpv` has to be on your `PATH`. It is the audio engine. Without it the player can list activities and then fail the moment you press Enter.

`playerctl` is optional. Install it if you want media keys, or if you want `playerctl next` from another window. The Python side of that is `dbus-next`, which the install pulls in. A session bus has to be running, which it already is on a normal desktop login.

## Install

```sh
git clone https://github.com/GCaggianese/brain-fm-tui
cd brain-fm-tui
uv sync
uv run brain-fm-tui --setup
uv run brain-fm-tui
```

[uv](https://docs.astral.sh/uv/) also installs pytest. `uv run pytest` runs the tests.

pip works if you would rather not use uv. From the clone:

```sh
pip install .
brain-fm-tui --setup
brain-fm-tui
```

That installs the player only.

## The session cookie

There is no login form. Brain.fm's session is a cookie named `token`, and you copy it yourself.

Sign in on the website in a normal browser. Open developer tools and the Network panel, then reload the page. One request is the document, the page itself, not a script or an image. Open that request. In its Cookies section, `token` is the last entry. Copy the value, not the name.

```sh
brain-fm-tui --setup
```

The prompt is `paste your cookie here:`. Typing is hidden, the way a password prompt is, so the line stays blank while you paste. Press Enter. A value that is not a token is rejected, and the command exits without saving it. A good paste prints `saved` and nothing else.

The file is `~/.local/share/brain-fm-tui/session`, readable only by your user. The cookie lasts about fifteen minutes. When it expires, playback stops and the player says the session expired. Copy a new one and run `--setup` again.

Ctrl+R re-reads that file. It does not open a window, and it does not sign you in. If the file is still the old cookie, Ctrl+R has nothing new to find.

## Playing

Tab and Shift+Tab move between Focus, Relax, Sleep, and Meditate. Each tab lists the activities that belong to it. Enter starts the highlighted one. The lines above the list are the track the server actually sent: title, category, activity, genre, length, and tempo. They are not a copy of the menu item you picked.

Space pauses. `n` skips to the next track in the queue the server already handed over. When the track finishes, the next one starts on its own. `q` quits and stops mpv. Ctrl+P opens Textual's command palette.

The row under the track is the neural-effect mix for the category you are looking at.

`a` toggles ADHD mode. On the website that is not a separate stream. It means the mix for that category is High, and only High. Turning it off clears the mix rather than switching you to Medium.

`1`, `2`, and `3` toggle Low, Medium, and High on their own. More than one can be on. A filled dot is selected, an empty one is not. Ticking Low or Medium while ADHD is on turns ADHD off, because the mix is no longer High alone. The same thing happens on the website, which is why their player shows a toast about it.

The mix is saved to the same account preference the website reads, and each category keeps its own. Focus can be High while Sleep is Low. If you change the mix for a category that is already playing, the player starts that session again so the new mix applies. If it is not playing, the next track you start in that tab picks it up.

## playerctl

`playerctl play`, `pause`, `next`, and volume talk to this player, not to a bare mpv process. That matters for next. A session arrives with a queue of tracks. `playerctl next` and the `n` key both play the following one. They do not reload the song you are already hearing.

The MPRIS name is `brainfm`. If something else already owns that name, the footer shows the name this player used instead. Point playerctl at that name.

## License

Apache-2.0. The text is in [`LICENSE`](LICENSE).
