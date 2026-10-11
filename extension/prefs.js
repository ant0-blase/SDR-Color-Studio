// SDR Color Studio preferences — GNOME Shell 51, GTK4/libadwaita.
// Launched by GNOME Extensions in a separate process (not in gnome-shell).
import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Gtk from 'gi://Gtk';
import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

// Translation data follows the user's locale, with English fallback for unknown locales.
function getTranslator(settings) {
    let catalog = {};
    try {
        const path = GLib.build_filenamev([GLib.get_home_dir(), '.local', 'share',
            'gnome-shell', 'extensions', 'sdr-color-studio@local', 'i18n.json']);
        const [ok, bytes] = Gio.File.new_for_path(path).load_contents(null);
        if (ok)
            catalog = JSON.parse(new TextDecoder().decode(bytes));
    } catch (error) {
        console.warn(`[SDR Color Studio] localization unavailable: ${error}`);
    }
    const override = settings.get_string('language');
    const env = (GLib.get_language_names()?.[0] ?? 'en').replace('-', '_');
    const requested = override === 'system' ? env : override;
    const locale = requested.toLowerCase().startsWith('pt_br') ? 'pt_BR' : requested.split('_')[0];
    const translation = catalog[locale] ?? catalog.en ?? {};
    const english = catalog.en ?? {};
    return text => locale === 'fr' ? text : (translation[text] ?? english[text] ?? text);
}

const LOCALES = [
    ['system', 'System language'], ['en', 'English'], ['fr', 'Français'],
    ['de', 'Deutsch'], ['es', 'Español'], ['it', 'Italiano'], ['pt_BR', 'Português (Brasil)'],
];

const REFERENCE_NITS = 203;
const MAX_UI_NITS = 1600;
const FIELDS = [
    {key: 'saturation', title: 'Saturation', min: 0, max: 2, step: 0.01, defaultValue: 1, percent: true},
    {key: 'contrast', title: 'Contraste', min: 0.5, max: 1.5, step: 0.01, defaultValue: 1, percent: true},
    {key: 'gamma', title: 'Gamma', min: 0.6, max: 1.6, step: 0.01, defaultValue: 1, percent: true},
    {key: 'brightness', title: 'Luminosité logicielle', min: -0.25, max: 0.25, step: 0.01, defaultValue: 0, percent: false},
];

function runGdctl(...args) {
    try {
        const proc = Gio.Subprocess.new(
            ['gdctl', ...args],
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
        const [, stdout, stderr] = proc.communicate_utf8(null, null);
        return {ok: proc.get_successful(), output: stdout ?? '', error: (stderr ?? '').trim()};
    } catch (error) {
        return {ok: false, output: '', error: String(error)};
    }
}

function inspectMonitors() {
    const result = runGdctl('show', '--verbose');
    const monitors = [];
    const limits = {};
    const modes = {};
    if (!result.ok)
        return {monitors, limits, modes, error: result.error || 'gdctl show a échoué'};

    let current = null;
    let inBacklight = false;
    for (const line of result.output.split('\n')) {
        const header = line.match(/\bMonitor\s+([^\s(]+)\s+\(/);
        if (header) {
            current = header[1];
            if (!monitors.includes(current))
                monitors.push(current);
            inBacklight = false;
        }
        if (!current)
            continue;
        if (line.includes('Backlight:')) {
            inBacklight = true;
            limits[current] = {};
            continue;
        }
        if (line.includes('color-mode ⇒')) {
            const found = line.match(/color-mode\s*⇒\s*([^\s]+)/);
            if (found)
                modes[current] = found[1];
        }
        if (!inBacklight)
            continue;
        const entry = line.match(/\b(min|max|value)\s*⇒\s*(\d+)/);
        if (entry)
            limits[current][entry[1]] = Number(entry[2]);
        if (line.includes('Properties:') || line.includes('Logical monitors:'))
            inBacklight = false;
    }
    return {monitors, limits, modes, error: ''};
}

function loadProfiles(settings) {
    try {
        const parsed = JSON.parse(settings.get_string('monitor-profiles'));
        return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
    } catch (_error) {
        return {};
    }
}

function labeledScale(minimum, maximum, step) {
    const scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, minimum, maximum, step);
    scale.set_draw_value(false);
    scale.set_size_request(245, -1);
    scale.set_hexpand(true);
    scale.set_valign(Gtk.Align.CENTER);
    return scale;
}

function controlRow(title, scale, suffix) {
    const row = new Adw.ActionRow({title});
    row.add_suffix(scale);
    row.add_suffix(suffix);
    return row;
}

export default class SDRColorStudioPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        const t = getTranslator(settings);
        // Keep the settings object alive for the whole preferences window lifetime.
        window._sdrColorSettings = settings;
        window.set_default_size(720, 700);

        const found = inspectMonitors();
        const savedProfiles = loadProfiles(settings);
        const monitors = found.monitors.length ? found.monitors :
            (Object.keys(savedProfiles).length ? Object.keys(savedProfiles) : ['monitor-0']);
        let loading = false;
        let profiles = savedProfiles;

        const page = new Adw.PreferencesPage({title: t('SDR Color Studio'), icon_name: 'video-display-symbolic'});
        window.add(page);
        const displayGroup = new Adw.PreferencesGroup({
            title: t('Écran'),
            description: t('Les réglages de couleur sont indépendants pour chaque écran.'),
        });
        page.add(displayGroup);
        const langRow = new Adw.ActionRow({title: 'Language / Langue',
            subtitle: 'Reopen the preferences window to apply a new language.'});
        const langMenu = Gtk.DropDown.new_from_strings(LOCALES.map(([, label]) => label));
        const selectedLang = settings.get_string('language');
        langMenu.set_selected(Math.max(0, LOCALES.findIndex(([code]) => code === selectedLang)));
        langMenu.connect('notify::selected', () => {
            settings.set_string('language', LOCALES[langMenu.get_selected()][0]);
        });
        langRow.add_suffix(langMenu);
        displayGroup.add(langRow);
        const monitorRow = new Adw.ActionRow({title: t('Moniteur')});
        const monitorMenu = Gtk.DropDown.new_from_strings(monitors);
        monitorMenu.set_valign(Gtk.Align.CENTER);
        monitorRow.add_suffix(monitorMenu);
        displayGroup.add(monitorRow);

        const enabledRow = new Adw.SwitchRow({title: t('Activer la correction colorimétrique')});
        displayGroup.add(enabledRow);
        settings.bind('enabled', enabledRow, 'active', Gio.SettingsBindFlags.DEFAULT);

        const protectRow = new Adw.SwitchRow({
            title: t('Protéger les applications en plein écran'),
            subtitle: t('Coupe le shader pendant tout plein écran (HDR ou SDR). Ne détecte pas les vidéos HDR en fenêtre.'),
        });
        displayGroup.add(protectRow);
        settings.bind('protect-fullscreen', protectRow, 'active', Gio.SettingsBindFlags.DEFAULT);

        const colors = new Adw.PreferencesGroup({
            title: t('Couleurs'),
            description: t('Les changements sont enregistrés et envoyés à l’extension automatiquement.'),
        });
        page.add(colors);
        const sliders = {};
        const labels = {};
        const currentMonitor = () => monitors[monitorMenu.get_selected()] ?? monitors[0];
        const updateLabel = (field, value) => {
            const suffix = field.percent ? `${Math.round(value * 100)} %` : value.toFixed(2);
            labels[field.key].set_text(suffix);
        };

        for (const field of FIELDS) {
            const scale = labeledScale(field.min, field.max, field.step);
            const label = new Gtk.Label({width_chars: 7, xalign: 1});
            sliders[field.key] = scale;
            labels[field.key] = label;
            colors.add(controlRow(t(field.title), scale, label));
            scale.connect('value-changed', () => {
                const value = Math.round(scale.get_value() * 1000) / 1000;
                updateLabel(field, value);
                if (loading)
                    return;
                const connector = currentMonitor();
                const profile = {...(profiles[connector] ?? {})};
                profile[field.key] = value;
                profiles = {...profiles, [connector]: profile};
                settings.set_string('monitor-profiles', JSON.stringify(profiles));
            });
        }

        const white = new Adw.PreferencesGroup({
            title: t('Maximum SDR Brightness (référence)'),
            description: t('Échelle de référence PQ, non mesurée. À régler par écran. Le signal HDR conserve sa plage dynamique physique.'),
        });
        page.add(white);
        const whiteScale = labeledScale(80, MAX_UI_NITS, 1);
        const whiteLabel = new Gtk.Label({width_chars: 10, xalign: 1});
        white.add(controlRow(t('Blanc SDR maximal demandé'), whiteScale, whiteLabel));
        whiteScale.connect('value-changed', () => {
            whiteLabel.set_text(`${Math.round(whiteScale.get_value())} nits`);
        });
        const limitsRow = new Adw.ActionRow({title: t('Plage disponible')});
        white.add(limitsRow);
        const applyRow = new Adw.ActionRow({title: t('Appliquer le blanc SDR')});
        const applyButton = new Gtk.Button({label: t('Appliquer'), valign: Gtk.Align.CENTER});
        applyRow.add_suffix(applyButton);
        white.add(applyRow);
        const statusRow = new Adw.ActionRow({title: t('État')});
        white.add(statusRow);
        const status = message => statusRow.set_subtitle(message);

        const resetGroup = new Adw.PreferencesGroup({title: t('Actions')});
        page.add(resetGroup);
        const resetRow = new Adw.ActionRow({title: t('Réinitialiser les couleurs de cet écran')});
        const resetButton = new Gtk.Button({label: t('Réinitialiser'), valign: Gtk.Align.CENTER});
        resetRow.add_suffix(resetButton);
        resetGroup.add(resetRow);
        const openRow = new Adw.ActionRow({
            title: t('Application complète'),
            subtitle: t('Mires HDR10 de test, réglages et suggestion EDID dans la GUI GTK4.'),
        });
        const openButton = new Gtk.Button({label: t('Ouvrir'), valign: Gtk.Align.CENTER});
        openRow.add_suffix(openButton);
        resetGroup.add(openRow);

        const refreshMonitor = () => {
            loading = true;
            const connector = currentMonitor();
            profiles = loadProfiles(settings);
            const profile = profiles[connector] ?? {};
            for (const field of FIELDS) {
                const raw = Number(profile[field.key] ?? field.defaultValue);
                const value = Number.isFinite(raw) ? Math.max(field.min, Math.min(field.max, raw)) : field.defaultValue;
                sliders[field.key].set_value(value);
                updateLabel(field, value);
            }
            const range = found.limits[connector];
            if (range && Number.isFinite(range.value))
                whiteScale.set_value(Math.min(MAX_UI_NITS, Math.max(80, Math.round(range.value * REFERENCE_NITS / 100))));
            else
                whiteScale.set_value(REFERENCE_NITS);
            const hdrMode = found.modes[connector] ?? 'inconnu';
            if (!range || !Number.isFinite(range.min) || !Number.isFinite(range.max)) {
                limitsRow.set_subtitle(`${connector} : contrôle gdctl Backlight non disponible (mode ${hdrMode})`);
                applyButton.set_sensitive(false);
            } else {
                limitsRow.set_subtitle(`${connector} : gdctl ${range.min}–${range.max} (~${Math.round(range.max * REFERENCE_NITS / 100)} nits demandés), mode ${hdrMode}`);
                applyButton.set_sensitive(hdrMode === 'bt2100');
            }
            status(found.error || 'Mode de protection : pause du shader en plein écran. Les vidéos HDR en fenêtre peuvent encore être modifiées.');
            loading = false;
        };
        monitorMenu.connect('notify::selected', refreshMonitor);
        settings.connect('changed::monitor-profiles', () => {
            if (!loading)
                refreshMonitor();
        });
        resetButton.connect('clicked', () => {
            const connector = currentMonitor();
            const profile = {};
            for (const field of FIELDS)
                profile[field.key] = field.defaultValue;
            profiles = {...profiles, [connector]: profile};
            settings.set_string('monitor-profiles', JSON.stringify(profiles));
            status(`Réglages de couleur réinitialisés pour ${connector}. Le blanc SDR est inchangé.`);
        });
        applyButton.connect('clicked', () => {
            const connector = currentMonitor();
            const range = found.limits[connector];
            if (!range) {
                status('Aucun contrôle Backlight disponible pour cet écran.');
                return;
            }
            const requested = Math.round(whiteScale.get_value());
            const raw = Math.round(requested * 100 / REFERENCE_NITS);
            if (raw < range.min || raw > range.max) {
                status(`Limite Mutter : ${range.min}–${range.max}. ${requested} nits demandés exigeraient gdctl ${raw}.`);
                return;
            }
            const result = runGdctl('prefs', '--monitor', connector, '--backlight', String(raw));
            if (!result.ok) {
                status(`Échec gdctl : ${result.error || result.output.trim()}`);
                return;
            }
            range.value = raw;
            status(`${requested} nits de référence demandés (gdctl ${raw}) sur ${connector}. Aucun pic HDR physique garanti.`);
        });
        openButton.connect('clicked', () => {
            const path = GLib.build_filenamev([GLib.get_home_dir(), '.local', 'bin', 'sdr-color-studio']);
            if (!GLib.file_test(path, GLib.FileTest.IS_EXECUTABLE)) {
                status('Application externe introuvable. Réexécute ./install.sh.');
                return;
            }
            try {
                Gio.Subprocess.new([path], Gio.SubprocessFlags.NONE);
                status('Panneau SDR Color Studio ouvert.');
            } catch (error) {
                status(`Impossible d’ouvrir le panneau : ${error}`);
            }
        });

        refreshMonitor();
    }
}
