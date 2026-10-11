#!/usr/bin/env python3
"""GNOME 51 SDR Color Studio — unprivileged GTK4/libadwaita control panel."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Gtk, Adw, Gio, GLib
except (ImportError, ValueError) as exc:
    sys.exit(f"Dépendances manquantes (python-gobject gtk4 libadwaita) : {exc}")

def select_language(settings) -> str:
    override = settings.get_string('language')
    if override != 'system':
        requested = override
    else:
        requested = (os.environ.get('LANGUAGE', '').split(':')[0]
                     or os.environ.get('LC_ALL', '')
                     or os.environ.get('LC_MESSAGES', '')
                     or os.environ.get('LANG', 'en'))
    locale = requested.replace('-', '_').split('.')[0]
    if locale.lower().startswith('pt_br'):
        return 'pt_BR'
    return locale.split('_')[0]


def get_translator(settings):
    try:
        catalog = json.loads((Path.home() / '.local/share/gnome-shell/extensions/'
                              'sdr-color-studio@local/i18n.json').read_text())
    except (ValueError, OSError):
        catalog = {}
    language = select_language(settings)
    local = catalog.get(language, catalog.get('en', {}))
    english = catalog.get('en', {})
    return lambda text: (text if language == 'fr' else local.get(text, english.get(text, text)))


SCHEMA = 'org.gnome.shell.extensions.sdr-color-studio'
EXT = Path.home() / '.local/share/gnome-shell/extensions/sdr-color-studio@local'
SCHEMA_DIR = EXT / 'schemas'
REFERENCE_NITS = 203  # GNOME Mutter BT.2100 PQ reference white in 51.0.
LIMIT_NITS = 1600      # UI bound, not a measured physical luminance.
FIELDS = (
    ('saturation', 'Saturation', 0.0, 2.0, 0.01, 1.0),
    ('contrast', 'Contraste', 0.5, 1.5, 0.01, 1.0),
    ('gamma', 'Gamma', 0.6, 1.6, 0.01, 1.0),
    ('brightness', 'Luminosité logicielle', -0.25, 0.25, 0.01, 0.0),
)


def run(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def get_settings() -> Gio.Settings:
    if not (SCHEMA_DIR / 'gschemas.compiled').is_file():
        raise RuntimeError('Schéma GSettings absent : lance ./install.sh')
    source = Gio.SettingsSchemaSource.new_from_directory(
        str(SCHEMA_DIR), Gio.SettingsSchemaSource.get_default(), False)
    schema = source.lookup(SCHEMA, False)
    if not schema:
        raise RuntimeError(f'Schéma {SCHEMA} introuvable')
    return Gio.Settings.new_full(schema, None, None)


def monitors_and_limits() -> tuple[list[str], dict[str, tuple[int, int]]]:
    output = run('gdctl', 'show', '--verbose')
    if output.returncode:
        return ['eDP-1'], {}
    names: list[str] = []
    limits: dict[str, tuple[int, int]] = {}
    current = None
    is_backlight = False
    minval, maxval = None, None
    for line in output.stdout.splitlines():
        found = re.search(r'\bMonitor\s+([^\s(]+)\s+\(', line)
        if found:
            if current and minval is not None and maxval is not None:
                limits[current] = (minval, maxval)
            current = found.group(1)
            if current not in names:
                names.append(current)
            is_backlight = False
            minval, maxval = None, None
        if not current:
            continue
        if 'Backlight:' in line:
            is_backlight = True
        elif is_backlight:
            match = re.search(r'\b(min|max)\s*⇒\s*(\d+)', line)
            if match:
                if match.group(1) == 'min':
                    minval = int(match.group(2))
                else:
                    maxval = int(match.group(2))
            # The first non-indented section terminates this property's context.
            if 'Properties:' in line or 'Logical monitors:' in line:
                is_backlight = False
    if current and minval is not None and maxval is not None:
        limits[current] = (minval, maxval)
    return names or ['eDP-1'], limits


def edid_peak_nits(connector: str) -> float | None:
    """Try CTA-861 desired content max luminance. This is NOT a measured peak."""
    if not shutil.which('edid-decode'):
        return None
    for path in Path('/sys/class/drm').glob('*/edid'):
        if path.parent.name.endswith('-' + connector) and path.exists():
            result = run('edid-decode', str(path))
            if result.returncode:
                continue
            patterns = (
                r'Desired content max luminance:\s*([\d.]+)',
                r'Max luminance:\s*([\d.]+)\s*(?:cd/m|nits)',
            )
            for pattern in patterns:
                m = re.search(pattern, result.stdout, re.IGNORECASE)
                if m:
                    nits = float(m.group(1))
                    if 80 <= nits <= 10000:
                        return nits
    return None


class StudioWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title('SDR Color Studio — GNOME 51')
        self.set_default_size(740, 690)
        self.settings = get_settings()
        self.tr = get_translator(self.settings)
        self.profiles = self._load_profiles()
        self.names, self.limits = monitors_and_limits()
        self.loading = False
        self.pending_timer = 0
        self.scales: dict[str, Gtk.Scale] = {}
        self.numeric_labels: dict[str, Gtk.Label] = {}

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label=self.tr('SDR Color Studio')))
        toolbar.add_top_bar(header)
        self.set_content(toolbar)
        page = Adw.PreferencesPage()
        toolbar.set_content(page)

        monitor_group = Adw.PreferencesGroup(title=self.tr('Écran'), description=self.tr('Les réglages de couleur sont mémorisés séparément pour chaque connecteur.'))
        page.add(monitor_group)
        monitor_row = Adw.ActionRow(title=self.tr('Moniteur'), subtitle=self.tr('Connecteur Wayland / Mutter'))
        self.monitor_model = Gtk.StringList.new(self.names)
        self.monitor_select = Gtk.DropDown(model=self.monitor_model)
        self.monitor_select.set_valign(Gtk.Align.CENTER)
        self.monitor_select.connect('notify::selected', self._monitor_changed)
        monitor_row.add_suffix(self.monitor_select)
        monitor_group.add(monitor_row)

        protection_group = Adw.PreferencesGroup(
            title=self.tr('Protection des contenus plein écran'),
            description=self.tr('La coloration globale des pixels n’identifie pas les surfaces HDR en fenêtre. En plein écran, désactive temporairement l’effet GLSL (sans toucher aux réglages gdctl).'))
        page.add(protection_group)
        protect_row = Adw.SwitchRow(title=self.tr('Ne pas modifier les applications en plein écran'),
                                    subtitle=self.tr('Protège vidéos et jeux fullscreen, HDR ou SDR (tous les moniteurs).'))
        self.settings.bind('protect-fullscreen', protect_row, 'active', Gio.SettingsBindFlags.DEFAULT)
        protection_group.add(protect_row)

        colors_group = Adw.PreferencesGroup(
            title=self.tr('Réglages couleurs en direct'),
            description=self.tr('Effet GLSL expérimental : les valeurs ne constituent pas un étalonnage colorimétrique HDR.'))
        page.add(colors_group)
        enable_row = Adw.ActionRow(title=self.tr('Activer le traitement'), subtitle=self.tr('Aucun effet après réinitialisation des curseurs.'))
        enable = Gtk.Switch(active=self.settings.get_boolean('enabled'), valign=Gtk.Align.CENTER)
        enable.connect('notify::active', lambda sw, _: self.settings.set_boolean('enabled', sw.get_active()))
        enable_row.add_suffix(enable)
        colors_group.add(enable_row)

        for key, label, low, high, step, _ in FIELDS:
            row = Adw.ActionRow(title=self.tr(label))
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, low, high, step)
            scale.set_draw_value(False)
            scale.set_size_request(270, -1)
            scale.set_hexpand(True)
            scale.set_valign(Gtk.Align.CENTER)
            scale.connect('value-changed', self._changed_value, key)
            value_label = Gtk.Label(width_chars=7, xalign=1)
            row.add_suffix(scale)
            row.add_suffix(value_label)
            colors_group.add(row)
            self.scales[key] = scale
            self.numeric_labels[key] = value_label

        hdr_group = Adw.PreferencesGroup(
            title=self.tr('Blanc SDR dans la sortie HDR'),
            description=self.tr('Le mode BT.2100 doit être actif. Valeurs nominales demandées à Mutter, non mesurées par une sonde.'))
        page.add(hdr_group)
        hdr_row = Adw.ActionRow(title=self.tr('Blanc SDR demandé'), subtitle=self.tr('203 nits = référence PQ de Mutter ; les pics HDR restent limités par la dalle.'))
        self.nits_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 80, LIMIT_NITS, 1)
        self.nits_scale.set_size_request(265, -1)
        self.nits_scale.set_draw_value(False)
        self.nits_scale.set_value(203)
        self.nits_scale.set_valign(Gtk.Align.CENTER)
        self.nits_label = Gtk.Label(label=self.tr('203 nits'), width_chars=10, xalign=1)
        self.nits_scale.connect('value-changed', lambda scale: self.nits_label.set_text(f'{round(scale.get_value())} nits'))
        hdr_row.add_suffix(self.nits_scale)
        hdr_row.add_suffix(self.nits_label)
        hdr_group.add(hdr_row)

        self.mode_info = Gtk.Label(xalign=0, wrap=True, selectable=True)
        hdr_group.add(self._custom_row(self.mode_info))
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9, margin_top=8, margin_bottom=8)
        apply_btn = Gtk.Button(label=self.tr('Appliquer le blanc SDR'), css_classes=['suggested-action'])
        apply_btn.connect('clicked', self._apply_white)
        action_box.append(apply_btn)
        detect_btn = Gtk.Button(label=self.tr('Suggestion EDID'))
        detect_btn.connect('clicked', self._suggest_edid)
        action_box.append(detect_btn)
        reset_btn = Gtk.Button(label=self.tr('Réinitialiser les couleurs'))
        reset_btn.connect('clicked', self._reset)
        action_box.append(reset_btn)
        hdr_group.add(self._custom_row(action_box))

        calibration_group = Adw.PreferencesGroup(
            title=self.tr('Mires HDR10 de calibration visuelle'),
            description=self.tr('Vidéo PQ 10 bits / BT.2020 avec paliers 100, 203, 400, 600, 1000, 1600 et 2000 nits. Une mire ne mesure pas la luminance réelle de la dalle.'))
        page.add(calibration_group)
        explain = Gtk.Label(xalign=0, wrap=True, selectable=True)
        explain.set_text(self.tr('Petit carré de référence à 203 nits en haut à gauche ; carré central à intensité variable, bandes proches du noir en bas. Chaque palier dure 1,5 s. Lire dans un lecteur qui sort du véritable HDR10.'))
        calibration_group.add(self._custom_row(explain))
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9,
                           margin_top=8, margin_bottom=8)
        create_button = Gtk.Button(label=self.tr('Générer la mire HDR10'))
        create_button.connect('clicked', self._generate_hdr_test)
        controls.append(create_button)
        play_button = Gtk.Button(label=self.tr('Lire la mire'))
        play_button.connect('clicked', self._play_hdr_test)
        controls.append(play_button)
        calibration_group.add(self._custom_row(controls))

        self.status = Gtk.Label(xalign=0, wrap=True, selectable=True)
        page.add(self._status_group(self.status))
        self._monitor_changed()

    @staticmethod
    def _custom_row(child: Gtk.Widget) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow(selectable=False, activatable=False)
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_start=12,
                            margin_end=12, margin_top=8, margin_bottom=8)
        container.append(child)
        row.set_child(container)
        return row

    def _status_group(self, label: Gtk.Label) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=self.tr('Diagnostic'))
        group.add(self._custom_row(label))
        return group

    def _monitor(self) -> str:
        index = self.monitor_select.get_selected()
        return self.names[index] if index < len(self.names) else self.names[0]

    def _load_profiles(self) -> dict:
        try:
            data = json.loads(self.settings.get_string('monitor-profiles'))
            return data if isinstance(data, dict) else {}
        except (ValueError, TypeError):
            return {}

    def _monitor_changed(self, *_args):
        self.loading = True
        monitor = self._monitor()
        data = self.profiles.get(monitor, {})
        for key, _, _, _, _, default in FIELDS:
            value = data.get(key, default)
            try:
                self.scales[key].set_value(float(value))
            except (ValueError, TypeError):
                self.scales[key].set_value(default)
            self._set_label(key, self.scales[key].get_value())
        self.loading = False
        self._refresh_status()

    def _set_label(self, key: str, value: float):
        self.numeric_labels[key].set_text(f'{value * 100:.0f} %' if key in ('saturation', 'contrast', 'gamma') else f'{value:+.2f}')

    def _changed_value(self, scale: Gtk.Scale, key: str):
        value = scale.get_value()
        self._set_label(key, value)
        if self.loading:
            return
        monitor = self._monitor()
        data = self.profiles.setdefault(monitor, {})
        data[key] = round(value, 3)
        if self.pending_timer:
            GLib.source_remove(self.pending_timer)
        self.pending_timer = GLib.timeout_add(65, self._save_profiles)

    def _save_profiles(self) -> bool:
        self.pending_timer = 0
        self.settings.set_string('monitor-profiles', json.dumps(self.profiles, sort_keys=True))
        return GLib.SOURCE_REMOVE

    def _refresh_status(self):
        connector = self._monitor()
        minimum, maximum = self.limits.get(connector, (10, 210))
        cap_nits = round(maximum * REFERENCE_NITS / 100)
        self.mode_info.set_text(
            f'{connector} : plage Mutter actuelle {minimum}–{maximum}, soit jusqu’à ~{cap_nits} nits demandés. '
            + ('Patch étendu détecté.' if maximum > 210 else 'Pour dépasser ~426 nits, compiler le patch Mutter optionnel.'))
        self.status.set_text(
            'Saturation / contraste / gamma : effet visuel GNOME Shell, pas calibration. '
            'Le traitement peut également modifier les couleurs des vidéos HDR. '
            'La luminosité physique reste limitée par le matériel.')

    def _apply_white(self, _button):
        connector = self._monitor()
        nits = round(self.nits_scale.get_value())
        if connector not in self.limits:
            self.status.set_text(f"Aucun contrôle Backlight exposé pour {connector} : opération annulée.")
            return
        minv, maxv = self.limits[connector]
        raw = round(nits * 100 / REFERENCE_NITS)
        if not (minv <= raw <= maxv):
            self.status.set_text(
                f'{nits} nits demandés → gdctl {raw}, hors plage {minv}–{maxv}. '
                'Installe le patch Mutter si nécessaire ; aucune valeur n’a été changée.')
            return
        result = run('gdctl', 'prefs', '--monitor', connector, '--backlight', str(raw))
        if result.returncode:
            self.status.set_text('Échec gdctl : ' + (result.stderr.strip() or result.stdout.strip()))
        else:
            self.status.set_text(
                f'Envoyé à Mutter : {nits} nits SDR de référence (gdctl {raw}) sur {connector}. '
                'Ce n’est PAS une mesure de luminosité physique.')

    def _suggest_edid(self, _button):
        connector = self._monitor()
        estimate = edid_peak_nits(connector)
        if estimate is None:
            self.status.set_text('Pic HDR absent des métadonnées EDID accessibles ou edid-decode non installé. Utilise le réglage manuel.')
            return
        rounded = round(min(LIMIT_NITS, max(80, estimate)))
        self.nits_scale.set_value(rounded)
        self.status.set_text(
            f'EDID {connector} : « desired content max luminance » ≈ {estimate:.0f} nits. '
            'C’est une métadonnée indicative, pas une mesure du pic réel. Clique sur Appliquer pour essayer.')

    def _generate_hdr_test(self, button):
        generator = Path.home() / '.local/bin/sdr-color-studio-hdr-test'
        if not generator.is_file():
            self.status.set_text('Générateur absent : réexécute ./install.sh depuis v0.3.0.')
            return
        if not shutil.which('ffmpeg'):
            self.status.set_text('ffmpeg manquant : sudo pacman -S ffmpeg (encodeur libx265).')
            return
        if getattr(self, '_pattern_proc', None) is not None:
            self.status.set_text('Une génération de mire est déjà en cours.')
            return
        self.hdr_test_path = Path.home() / '.cache/sdr-color-studio/hdr10-test.mp4'
        button.set_sensitive(False)
        self.status.set_text('Création de la mire HDR10 via ffmpeg...')
        try:
            proc = Gio.Subprocess.new(
                [sys.executable, str(generator), '--output', str(self.hdr_test_path)],
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE)
            self._pattern_proc = proc
            def completed(process, result):
                try:
                    _, stdout, stderr = process.communicate_utf8_finish(result)
                    if process.get_successful():
                        self.status.set_text(f'Mire HDR10 créée : {self.hdr_test_path}. Lance un lecteur prenant en charge HDR10. {stdout.strip().splitlines()[0] if stdout.strip() else ""}')
                    else:
                        self.status.set_text('Échec de génération : ' + (stderr or stdout)[-900:])
                except GLib.Error as exc:
                    self.status.set_text(f'Échec de génération : {exc}')
                finally:
                    self._pattern_proc = None
                    button.set_sensitive(True)
            proc.communicate_utf8_async(None, None, completed)
        except GLib.Error as exc:
            self._pattern_proc = None
            button.set_sensitive(True)
            self.status.set_text(f'Impossible de lancer ffmpeg : {exc}')

    def _play_hdr_test(self, _button):
        path = Path.home() / '.cache/sdr-color-studio/hdr10-test.mp4'
        if not path.is_file():
            path = Path.home() / '.local/share/sdr-color-studio/hdr10-reference-steps.mp4'
        if not path.is_file():
            self.status.set_text('Mire HDR10 absente : réinstalle v0.3.0 ou génère-la.')
            return
        try:
            if shutil.which('mpv'):
                # --target-colorspace-hint requests HDR signalling where supported.
                Gio.Subprocess.new(['mpv', '--target-colorspace-hint=yes', str(path)],
                                   Gio.SubprocessFlags.NONE)
            else:
                Gio.AppInfo.launch_default_for_uri(Gio.File.new_for_path(str(path)).get_uri(), None)
            self.status.set_text('Mire ouverte. Vérifie dans le lecteur que la sortie reste HDR10 / PQ, sans tone mapping SDR.')
        except GLib.Error as exc:
            self.status.set_text(f'Lecture impossible : {exc}')

    def _reset(self, _button):
        monitor = self._monitor()
        self.profiles[monitor] = {key: default for key, _, _, _, _, default in FIELDS}
        self._monitor_changed()
        self._save_profiles()
        self.status.set_text(f'Couleurs réinitialisées pour {monitor}. Le niveau de blanc SDR gdctl est inchangé.')


class StudioApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='io.github.sdrcolor.Studio')
        self.window = None

    def do_activate(self):
        if self.window is None:
            self.window = StudioWindow(self)
        self.window.present()


if __name__ == '__main__':
    try:
        sys.exit(StudioApp().run(sys.argv))
    except (RuntimeError, OSError) as err:
        sys.exit(str(err))
