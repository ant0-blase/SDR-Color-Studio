import Clutter from 'gi://Clutter';
import Cogl from 'gi://Cogl';
import GObject from 'gi://GObject';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

// An offscreen color pass is an approximation, NOT a calibrated SDR/HDR transform.
// Six outputs is a practical GLSL-uniform bound, not a hardware restriction.
const SLOTS = 6;

const declarations = [
    'uniform float studio_monitor_count;',
];
for (let i = 0; i < SLOTS; i++) {
    declarations.push(`uniform vec4 studio_area_${i};`);
    declarations.push(`uniform vec4 studio_values_${i};`);
}

// Use normalized source-texture coordinates, avoiding a separate fullscreen pass
// for each connected monitor. The first display is the fallback/default.
const sample = [
    'vec2 uv = cogl_tex_coord0_in.st;',
    'vec4 values = vec4(1.0, 1.0, 1.0, 0.0);',
    'if (studio_monitor_count > 0.5) values = studio_values_0;',
];
for (let i = 1; i < SLOTS; i++) {
    sample.push(`if (studio_monitor_count > ${i}.5 &&
        uv.x >= studio_area_${i}.x &&
        uv.y >= studio_area_${i}.y &&
        uv.x < studio_area_${i}.x + studio_area_${i}.z &&
        uv.y < studio_area_${i}.y + studio_area_${i}.w)
        values = studio_values_${i};`);
}
const post = `
${sample.join('\n')}
// This is a display-referred, nonlinear effect for desktop appearance.
// Leave alpha intact, including semi-transparent desktop elements.
float saturation = clamp(values.x, 0.0, 2.0);
float contrast = clamp(values.y, 0.5, 1.5);
float gamma_value = clamp(values.z, 0.6, 1.6);
float brightness = clamp(values.w, -0.25, 0.25);
vec3 rgb = clamp(cogl_color_out.rgb, 0.0, 1.0);
rgb = pow(rgb, vec3(1.0 / gamma_value));
float Y = dot(rgb, vec3(0.2126, 0.7152, 0.0722));
rgb = vec3(Y) + (rgb - vec3(Y)) * saturation;
rgb = (rgb - vec3(0.5)) * contrast + vec3(0.5 + brightness);
cogl_color_out.rgb = clamp(rgb, 0.0, 1.0);
`;

const StudioEffect = GObject.registerClass(
class StudioEffect extends Clutter.ShaderEffect {
    vfunc_get_static_snippet() {
        const snippet = Cogl.Snippet.new(
            Cogl.SnippetHook.FRAGMENT, declarations.join('\n'), '');
        snippet.set_post(post);
        return snippet;
    }
});

function valuesFor(profiles, connector) {
    const p = profiles[connector] ?? {};
    return [
        Math.max(0, Math.min(2, Number(p.saturation ?? 1))),
        Math.max(0.5, Math.min(1.5, Number(p.contrast ?? 1))),
        Math.max(0.6, Math.min(1.6, Number(p.gamma ?? 1))),
        Math.max(-0.25, Math.min(0.25, Number(p.brightness ?? 0))),
    ];
}

export default class SdrColorStudio extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._effect = new StudioEffect();
        this._clone = new Clutter.Clone({
            source: Main.layoutManager.uiGroup,
            reactive: false,
            clip_to_allocation: true,
        });
        this._clone.visible = false; // Enable only when a profile differs from neutral.
        Shell.util_set_hidden_from_pick(this._clone, true);
        this._clone.add_constraint(new Clutter.BindConstraint({
            source: global.stage,
            coordinate: Clutter.BindCoordinate.SIZE,
        }));
        this._clone.add_effect(this._effect);
        global.stage.add_child(this._clone);
        this._changed = this._settings.connect('changed', () => this._apply());
        this._monitorsChanged = Main.layoutManager.connect(
            'monitors-changed', () => this._apply());
        // GNOME 51 exposes get_monitor_in_fullscreen() through layout monitors.
        // A full-screen HDR video must never be put through our experimental
        // SDR-like nonlinear grade. We cannot reliably identify HDR in a
        // windowed surface from a Shell extension, so this safeguard applies
        // conservatively to ANY fullscreen window (all monitors at once).
        this._fullscreenChanged = global.display.connect(
            'in-fullscreen-changed', () => this._apply());
        try {
            this._apply();
        } catch (err) {
            console.error(`[SDR Color Studio] Cannot initialize effect: ${err}`);
            this.disable();
        }
    }

    _connectorFor(index) {
        try {
            const manager = global.backend.get_monitor_manager();
            for (const logical of manager.get_logical_monitors()) {
                if (logical.get_number() !== index)
                    continue;
                const monitors = logical.get_monitors();
                if (monitors.length)
                    return monitors[0].get_connector();
            }
        } catch (err) {
            console.warn(`[SDR Color Studio] connector lookup: ${err}`);
        }
        return `monitor-${index}`;
    }

    _apply() {
        if (!this._effect)
            return;
        let profiles = {};
        try {
            profiles = JSON.parse(this._settings.get_string('monitor-profiles'));
            if (!profiles || typeof profiles !== 'object' || Array.isArray(profiles))
                profiles = {};
        } catch (err) {
            console.warn(`[SDR Color Studio] Invalid profiles JSON: ${err}`);
        }
        const enabled = this._settings.get_boolean('enabled');
        const screens = Main.layoutManager.monitors;
        const count = Math.min(screens.length, SLOTS);
        const stageWidth = Math.max(global.stage.width, 1);
        const stageHeight = Math.max(global.stage.height, 1);
        let hasAdjustment = false;
        for (let i = 0; i < SLOTS; i++) {
            const m = screens[i];
            const rect = m ? [
                m.x / stageWidth, m.y / stageHeight,
                m.width / stageWidth, m.height / stageHeight,
            ] : [0, 0, 0, 0];
            let val = m ? valuesFor(profiles, this._connectorFor(m.index)) : [1, 1, 1, 0];
            if (!enabled)
                val = [1, 1, 1, 0];
            if (m && (Math.abs(val[0] - 1) > 0.001 ||
                      Math.abs(val[1] - 1) > 0.001 ||
                      Math.abs(val[2] - 1) > 0.001 ||
                      Math.abs(val[3]) > 0.001))
                hasAdjustment = true;
            this._effect.set_uniform_float(`studio_area_${i}`, 4, rect);
            this._effect.set_uniform_float(`studio_values_${i}`, 4, val);
        }
        // A count of zero leaves all output unaltered.
        this._effect.set_uniform_float('studio_monitor_count', 1, [count]);
        const fullscreenProtected = this._settings.get_boolean('protect-fullscreen') &&
            screens.some(m => m.inFullscreen);
        this._clone.visible = enabled && hasAdjustment && !fullscreenProtected;
        if (this._clone.visible)
            this._effect.queue_repaint();
    }

    disable() {
        if (this._settings && this._changed)
            this._settings.disconnect(this._changed);
        if (this._monitorsChanged)
            Main.layoutManager.disconnect(this._monitorsChanged);
        if (this._fullscreenChanged)
            global.display.disconnect(this._fullscreenChanged);
        this._fullscreenChanged = 0;
        this._monitorsChanged = 0;
        this._changed = 0;
        if (this._clone) {
            this._clone.destroy();
            this._clone = null;
        }
        this._effect = null;
        this._settings = null;
    }
}
