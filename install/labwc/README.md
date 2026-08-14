# labwc Configuration

This directory contains the custom `labwc` configuration required for the
James City Bruton Volunteer Fire Department Station Dashboard.

These files are installed in the user's home directory under:

~/.config/labwc/

The dashboard also uses a Kanshi configuration stored in:

install/kanshi/config

which is installed under:

~/.config/kanshi/

---

## Files

### autostart

Starts the desktop components required by the dashboard.

It is responsible for:

- Starting `kanshi`
- Running `lxsession-xdg-autostart`
- Launching Chromium using:

`~/station-dashboard/scripts/start-browser.sh`

- Automatically hiding the mouse cursor after startup using `wtype`

---

### rc.xml

Extends the default `labwc` keyboard configuration.

It adds one custom keybinding:

`Alt + Super + H`

This keybinding executes:

- `HideCursor`
- `WarpCursor`

to hide the mouse pointer and move it off-screen.

The default `labwc` keyboard shortcuts are preserved using:

`<default />`

No other keyboard shortcuts are modified.

---

### Kanshi configuration

The Kanshi configuration is stored in:

`install/kanshi/config`

It configures the station display to use:

`1920x1080 @ 60 Hz`

The configuration is installed in:

`~/.config/kanshi/config`

This provides a readable 1080p display on the station television while
maintaining a 60 Hz refresh rate.

---

## Why this is needed

The traditional Linux utility `unclutter` only works with X11.

The Station Dashboard runs under:

- Wayland
- labwc

Instead of using compatibility layers or background daemons, the dashboard uses
labwc's native cursor hiding capability.

The cursor is hidden automatically during startup by simulating the
`Alt + Super + H` key combination using `wtype`.

This approach:

- Uses native Wayland functionality
- Does not require X11
- Does not require `unclutter`
- Has proven reliable during testing

The dashboard uses Kanshi to automatically configure the station television
to the desired display resolution when the graphical session starts.

---

## Installing

Copy the labwc configuration files into:

`~/.config/labwc/`

For example:

`cp autostart ~/.config/labwc/`
`cp rc.xml ~/.config/labwc/`

Install the Kanshi configuration:

`mkdir -p ~/.config/kanshi`
`cp ../kanshi/config ~/.config/kanshi/`

Reload labwc:

`labwc --reconfigure`

or simply reboot.

---

## Dependencies

The automatic cursor hiding requires:

`wtype`

Install with:

`sudo apt install wtype`

The display configuration requires:

`kanshi`

---

## Display Configuration

The current station display configuration is:

`HDMI-A-1`
`1920x1080`
`60 Hz`

The configuration is intentionally maintained in the repository so that the
station display setup can be reproduced if the Raspberry Pi is replaced or
the dashboard is installed on another system.

---

## Version

Display configuration added in:

**Version 1.3.3**
