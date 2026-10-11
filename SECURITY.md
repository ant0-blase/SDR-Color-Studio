# Security

This experimental patch replaces Mutter, GNOME's compositor; it can make
a graphical session unusable. Only install packages you built and reviewed.
The build script fetches Arch packaging over HTTPS and asks the local
`makepkg` to verify the original package sources. It does not auto-install.
Keep system packages updated; don't permanently pin Mutter via `IgnorePkg`.
Do not run `makepkg` as root. If a graphical session fails, use Ctrl+Alt+F3
and restore the official package with `sudo pacman -S mutter`.
