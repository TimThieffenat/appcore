"""Traduction des textes du socle : espagnol (voir appcore/i18n.py).

Clé : le texte anglais du code ; valeur : sa traduction (un pluriel :
(singulier, pluriel)). Les champs {nom} doivent rester tels quels. Les textes
propres à une app sont dans le locales/ de l'app. Après un changement de
texte : python appcore/tools/i18n_check.py --core."""
# ruff: noqa: E501

T = {
    # --- appcore/boot.py
    '{app} could not start': '{app} no pudo iniciarse',
    '{app} stopped last time': '{app} se detuvo la última vez',
    # --- appcore/crash_report.py
    'Send by email opens your email app with this report, addressed to {email}. Nothing is sent until you press Send.': '«Enviar por correo» abre tu app de correo con este informe, dirigido a {email}. No se envía nada hasta que pulses Enviar.',
    'Send by email': 'Enviar por correo',
    'Copy': 'Copiar',
    'Close': 'Cerrar',
    'What were you doing when the problem happened? (optional)': '¿Qué estabas haciendo cuando ocurrió el problema? (opcional)',
    'Clear': 'Borrar',
    'Erase the errors and the log (after sending them)': 'Borra los errores y el registro (después de enviarlos)',
    'Copied.': 'Copiado.',
    'Cleared.': 'Borrado.',
    'Your email app opens. The report is also copied, in case it is cut.': 'Se abre tu app de correo. El informe también se ha copiado, por si se corta.',
    'No email app found. The report is copied: paste it in an email to {email}.': 'No se encontró ninguna app de correo. El informe está copiado: pégalo en un correo a {email}.',
    # --- appcore/music_theory.py
    'Letters (C D E)': 'Letras (C D E)',
    '{root} {scale}': '{root} {scale}',
    '{root} {mode}': '{root} {mode}',
    'Solfège ({notes})': 'Solfeo ({notes})',
    'major': 'mayor',
    'minor': 'menor',
    # --- appcore/page_settings.py
    'Same as phone': 'Como el teléfono',
    'Light (pastel)': 'Claro (pastel)',
    'Dark (neon)': 'Oscuro (neón)',
    'Settings': 'Ajustes',
    'Same as phone ({language})': 'Como el teléfono ({language})',
    'Language': 'Idioma',
    'Theme': 'Tema',
    'Note names': 'Nombres de notas',
    'Show': 'Mostrar',
    'What went wrong and what the app did, to send by email if the app misbehaves': 'Qué ha fallado y qué ha hecho la app, para enviarlo por correo si la app no funciona bien',
    'Error report': 'Informe de errores',
    'Instrument': 'Instrumento',
    'Guitars: FluidR3_GM by Frank Wen (CC BY 3.0) · Symbols: DejaVu Sans (Bitstream Vera license)': 'Guitarras: FluidR3_GM de Frank Wen (CC BY 3.0) · Símbolos: DejaVu Sans (licencia Bitstream Vera)',
    # --- instruments
    'Steel-string acoustic': 'Acústica de cuerdas de acero',
    'Nylon-string (classical)': 'Cuerdas de nailon (clásica)',
    'Soft keys (all musicians)': 'Teclado suave (todos los músicos)',
    # --- music_theory: chords
    'Major': 'Mayor',
    'Minor': 'Menor',
    'Diminished': 'Disminuido',
    'Augmented': 'Aumentado',
    'Sus2': 'Sus2',
    'Sus4': 'Sus4',
    '6': '6',
    'Minor 6': 'Menor 6',
    '7 (dominant)': '7 (dominante)',
    'Major 7': 'Mayor 7',
    'Minor 7': 'Menor 7',
    'Half-diminished (m7♭5)': 'Semidisminuido (m7♭5)',
    'Diminished 7': '7 disminuido',
    'Minor-major 7': 'Menor-mayor 7',
    '7sus4': '7sus4',
    'add9': 'add9',
    '9': '9',
    'Major 9': 'Mayor 9',
    'Minor 9': 'Menor 9',
    # --- music_theory: modes
    'Scale': 'Escala',
    'Chord': 'Acorde',
    # --- music_theory: scales
    'Major (Ionian)': 'Mayor (jónica)',
    'Natural minor (Aeolian)': 'Menor natural (eólica)',
    'Harmonic minor': 'Menor armónica',
    'Melodic minor': 'Menor melódica',
    'Major pentatonic': 'Pentatónica mayor',
    'Minor pentatonic': 'Pentatónica menor',
    'Minor blues': 'Blues menor',
    'Major blues': 'Blues mayor',
    'Dorian': 'Dórica',
    'Phrygian': 'Frigia',
    'Lydian': 'Lidia',
    'Mixolydian': 'Mixolidia',
    'Locrian': 'Locria',
    'Phrygian dominant': 'Frigia dominante',
    # --- music_theory: tunings
    'Standard (E A D G B E)': 'Estándar (E A D G B E)',
    'Drop D (D A D G B E)': 'Drop D (D A D G B E)',
    'Half step down (E♭)': 'Medio tono abajo (E♭)',
    'DADGAD': 'DADGAD',
    'Open G (D G D G B D)': 'Open G (D G D G B D)',
    'Open D (D A D F# A D)': 'Open D (D A D F# A D)',
}
