from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
automations = (ROOT / 'automations.yaml').read_text(encoding='utf-8')
input_select = (ROOT / 'input_select.yaml').read_text(encoding='utf-8')
input_boolean = (ROOT / 'input_boolean.yaml').read_text(encoding='utf-8')
input_text = (ROOT / 'input_text.yaml').read_text(encoding='utf-8')
input_datetime = (ROOT / 'input_datetime.yaml').read_text(encoding='utf-8')
docs_runtime = (ROOT / 'docs' / 'ac-produccion-manual-auto.md').read_text(encoding='utf-8')
docs_context = (ROOT / 'docs' / 'ac-aprendido-contexto.md').read_text(encoding='utf-8')

checks = []

def check(name, condition, detail):
    checks.append((name, bool(condition), detail))

def extract_input_select_options(entity_id):
    match = re.search(
        rf'^{re.escape(entity_id)}:\n(?P<body>(?:^[ \t].*\n?)*)',
        input_select,
        re.MULTILINE,
    )
    if not match:
        return None

    body = match.group('body')
    options_match = re.search(
        r'^\s+options:\n(?P<options>(?:^\s+- .*\n)+)',
        body,
        re.MULTILINE,
    )
    if not options_match:
        return []

    return [
        line.strip()[2:]
        for line in options_match.group('options').splitlines()
        if line.strip().startswith('- ')
    ]

# Escenario 1 y 2: manual ON
check(
    'manual_on_detecta_origen_manual',
    "value: manual_on" in automations and "value: manual_on_detected" in automations,
    'El guard de encendido manual marca origen manual_on y semilla manual_on_detected.'
)
check(
    'manual_on_clasifica_presence_gap',
    all(token in automations for token in [
        'manual_on_due_to_presence_gap_cool',
        'manual_on_due_to_presence_gap_heat',
        'manual_on_due_to_presence_gap',
    ]),
    'La clasificación contempla brecha de presencia por modo final.'
)
check(
    'manual_on_clasifica_comfort_gap',
    all(token in automations for token in [
        'manual_on_due_to_comfort_gap_cool',
        'manual_on_due_to_comfort_gap_heat',
    ]),
    'La clasificación contempla brecha de confort cuando sí hay presencia.'
)
check(
    'manual_on_extiende_presencia_temporal',
    'entity_id: input_datetime.ac_manual_presence_until' in automations,
    'El guard siempre actualiza ac_manual_presence_until al consolidar el encendido manual.'
)
check(
    'manual_on_no_notifica_fuera_presence_gap',
    all(token in automations for token in [
        "manual_event_type_final | trim) in ['manual_on_due_to_presence_gap','manual_on_due_to_presence_gap_cool','manual_on_due_to_presence_gap_heat']",
        'action: notify.mobile_app_samsung_s24',
        '{% else %}AC manual detectado: {{ final_mode }}{% endif %}',
    ]),
    'La única push del manual_on sigue confinada a la rama de presence gap; fuera de ella sólo queda telemetría local.'
)

# Escenario 3 y 4: manual OFF y auto OFF
check(
    'manual_off_detecta_origen_manual',
    "value: manual_off" in automations and 'manual_off_detected' in automations,
    'El guard de apagado manual marca origin=manual_off y clasifica el evento manual.'
)
check(
    'manual_off_ignora_auto_off',
    "state: 'on'\n      sequence:\n      - stop: 'Ignorado: AUTO OFF en curso.'" in automations,
    'El guard manual OFF aborta si la bandera ac_off_por_automatizacion está activa.'
)
check(
    'manual_off_aprende_cool_y_heat',
    all(token in automations for token in [
        'manual_off_feedback_valid_after_auto_on_cool',
        'manual_off_feedback_valid_after_auto_on_heat',
        'cool_on_after',
        'cool_off_after',
        'heat_on_after',
        'heat_off_after',
    ]),
    'El aprendizaje válido ajusta sesgos on/off y clasifica cool/heat.'
)
check(
    'manual_off_window_extendida',
    "ac_feedback_window_minutes:\n" in (ROOT / 'input_number.yaml').read_text(encoding='utf-8') and 'initial: 120' in (ROOT / 'input_number.yaml').read_text(encoding='utf-8') and "feedback_window_min: '{{ states(''input_number.ac_feedback_window_minutes'')" in automations,
    'La ventana de feedback OFF arranca en 120 minutos y las automatizaciones consumen el helper configurado.'
)

check(
    'manual_off_notificacion_unica_valida',
    automations.count('AC aprendió: OFF manual tras AUTO COOL') == 1 and automations.count('AC aprendió: OFF manual tras AUTO HEAT') == 1,
    'Sólo hay una notificación breve por aprendizaje válido en cada modo.'
)
check(
    'manual_off_pausa_5_min',
    'manual_off_hold_minutes: 5' in automations,
    'La automatización principal aplica una pausa anti-rebote de 5 minutos.'
)
check(
    'auto_off_30m_sin_contaminar_manual',
    'presence_away_30m' in automations and 'last_change_origin' in input_text,
    'La lógica principal distingue ausencia 30m y la telemetría mantiene origen separado.'
)


# Escenario 7: feedback manual de setpoint en cool
check(
    'manual_sp_feedback_detecta_cambio_temperature',
    all(token in automations for token in [
        'ac_cool_manual_setpoint_feedback',
        'attribute: temperature',
        'manual_sp_lower_than_auto',
        'manual_sp_higher_than_auto',
    ]),
    'Existe una ruta dedicada para cambios manuales de setpoint con clasificación arriba/abajo respecto al auto.'
)
check(
    'manual_sp_feedback_guarda_contexto_y_bucket',
    all(token in automations for token in [
        'cool_bucket_selected',
        'compact_context',
        'input_text.ac_cool_effective_setpoint_map',
        'SP auto=',
        'SP manual=',
        'ΔSP=',
    ]),
    'El feedback manual registra contexto resumido y persiste el bucket afectado para futuros autoencendidos.'
)
check(
    'manual_sp_feedback_distingue_fases_y_refuerzo',
    all(token in automations for token in [
        'ajuste_inmediato_post_auto_on',
        'ajuste_20_40_min',
        'refuerzo=sp_efectivo',
        'input_text.ac_cool_contextual_learning_map',
    ]),
    'La ruta diferencia feedback inmediato vs 20-40 min y refuerza el mapa contextual cuando bajar el SP revela falta de progreso.'
)

# Escenario 5 y 6: emergency + helpers
check(
    'helper_modo_no_fan_valido',
    extract_input_select_options('ac_ultimo_modo_no_fan') == ['off', 'cool', 'heat', 'emergency_cool'],
    'ac_ultimo_modo_no_fan admite exactamente y en orden `off`, `cool`, `heat`, `emergency_cool`.'
)
check(
    'reparacion_helper_invalido',
    'Autocorrige estados restaurados inválidos' in automations and "not in ['off','cool','heat','emergency_cool']" in automations,
    'Existe autocorrección para estados inválidos restaurados del helper.'
)
check(
    'docs_helper_runtime_exige_off_antes_normalizacion',
    all(token in docs_runtime for token in [
        'debe exponer únicamente `off`, `cool`, `heat`, `emergency_cool`',
        'probar manualmente `off` desde la UI de estados',
        'La automatización `AC - Normaliza helper último modo no fan` debe conservarse como red de seguridad',
    ]),
    'La documentación operativa exige validar `off` en runtime/UI antes de confiar en la automatización de normalización.'
)
check(
    'docs_contexto_no_acepta_false_legacy',
    all(token in docs_context for token in [
        '`off` es el único estado de reposo permitido para este helper',
        'No debe existir ninguna opción booleana como `False`/`false`',
        'primero hay que confirmar que el selector acepta `off`',
    ]),
    'La documentación de contexto mantiene que `off` es el único reposo válido y que `False` es legacy inválido.'
)
check(
    'banderas_auto_presentes',
    'ac_on_por_automatizacion' in input_boolean and 'ac_off_por_automatizacion' in input_boolean,
    'Las banderas de origen automático existen como helpers dedicados.'
)
check(
    'telemetria_input_text_presente',
    all(token in input_text for token in [
        'ac_last_auto_branch', 'ac_last_auto_action', 'ac_last_auto_mode',
        'ac_last_manual_event_type', 'ac_last_manual_learning_type', 'ac_last_change_origin'
    ]),
    'Los input_text críticos de telemetría están declarados.'
)
check(
    'manual_presence_helper_presente',
    'ac_manual_presence_until' in input_datetime,
    'El helper de presencia temporal manual existe.'
)
check(
    'emergency_cool_presente_y_latcheado',
    'emergency_latched' in automations and "option: 'emergency_cool'" in automations,
    'La lógica conserva un latch explícito para emergency_cool y persiste el helper sólo en esa rama.'
)

failed = [c for c in checks if not c[1]]
for name, ok, detail in checks:
    status = 'PASS' if ok else 'FAIL'
    print(f'[{status}] {name}: {detail}')

if failed:
    print(f'\nResultado: {len(failed)} chequeos fallaron de {len(checks)}.', file=sys.stderr)
    sys.exit(1)

print(f'\nResultado: {len(checks)} chequeos superados.')
