"""Traduction des textes du socle : italien (voir appcore/i18n.py).

Clé : le texte anglais du code ; valeur : sa traduction (un pluriel :
(singulier, pluriel)). Les champs {nom} doivent rester tels quels. Les textes
propres à une app sont dans le locales/ de l'app. Après un changement de
texte : python appcore/tools/i18n_check.py --core."""
# ruff: noqa: E501

T = {
    # --- appcore/boot.py
    '{app} could not start': '{app} non è riuscita ad avviarsi',
    '{app} stopped last time': "{app} si è chiusa l'ultima volta",
    # --- appcore/crash_report.py
    'Send by email opens your email app with this report, addressed to {email}. Nothing is sent until you press Send.': '«Invia per e-mail» apre la tua app di posta con questo rapporto, indirizzato a {email}. Non viene inviato nulla finché non premi Invia.',
    'Send by email': 'Invia per e-mail',
    'Copy': 'Copia',
    'Close': 'Chiudi',
    'What were you doing when the problem happened? (optional)': 'Cosa stavi facendo quando si è verificato il problema? (facoltativo)',
    'Clear': 'Cancella',
    'Erase the errors and the log (after sending them)': 'Cancella gli errori e il registro (dopo averli inviati)',
    'Copied.': 'Copiato.',
    'Cleared.': 'Cancellato.',
    'Your email app opens. The report is also copied, in case it is cut.': 'Si apre la tua app di posta. Il rapporto è anche copiato, nel caso venga tagliato.',
    'No email app found. The report is copied: paste it in an email to {email}.': "Nessuna app di posta trovata. Il rapporto è copiato: incollalo in un'e-mail a {email}.",
    # --- appcore/music_theory.py
    'Letters (C D E)': 'Lettere (C D E)',
    '{root} {scale}': '{root} {scale}',
    '{root} {mode}': '{root} {mode}',
    'Solfège ({notes})': 'Solfeggio ({notes})',
    'major': 'maggiore',
    'minor': 'minore',
    # --- appcore/page_settings.py
    'Same as phone': 'Come il telefono',
    'Light (pastel)': 'Chiaro (pastello)',
    'Dark (neon)': 'Scuro (neon)',
    'Settings': 'Impostazioni',
    'Same as phone ({language})': 'Come il telefono ({language})',
    'Language': 'Lingua',
    'Theme': 'Tema',
    'Note names': 'Nomi delle note',
    'Show': 'Mostra',
    'What went wrong and what the app did, to send by email if the app misbehaves': "Cosa è andato storto e cosa ha fatto l'app, da inviare per e-mail se l'app non funziona bene",
    'Error report': 'Rapporto errori',
    'Instrument': 'Strumento',
    'Guitars: FluidR3_GM by Frank Wen (CC BY 3.0) · Symbols: DejaVu Sans (Bitstream Vera license)': 'Chitarre: FluidR3_GM di Frank Wen (CC BY 3.0) · Simboli: DejaVu Sans (licenza Bitstream Vera)',
    # --- instruments
    'Steel-string acoustic': 'Acustica con corde in acciaio',
    'Nylon-string (classical)': 'Corde in nylon (classica)',
    'Soft keys (all musicians)': 'Tastiera morbida (tutti i musicisti)',
    # --- music_theory: chords
    'Major': 'Maggiore',
    'Minor': 'Minore',
    'Diminished': 'Diminuito',
    'Augmented': 'Aumentato',
    'Sus2': 'Sus2',
    'Sus4': 'Sus4',
    '6': '6',
    'Minor 6': 'Minore 6',
    '7 (dominant)': '7 (dominante)',
    'Major 7': 'Maggiore 7',
    'Minor 7': 'Minore 7',
    'Half-diminished (m7♭5)': 'Semidiminuito (m7♭5)',
    'Diminished 7': '7 diminuita',
    'Minor-major 7': 'Minore-maggiore 7',
    '7sus4': '7sus4',
    'add9': 'add9',
    '9': '9',
    'Major 9': 'Maggiore 9',
    'Minor 9': 'Minore 9',
    # --- music_theory: modes
    'Scale': 'Scala',
    'Chord': 'Accordo',
    # --- music_theory: scales
    'Major (Ionian)': 'Maggiore (ionica)',
    'Natural minor (Aeolian)': 'Minore naturale (eolia)',
    'Harmonic minor': 'Minore armonica',
    'Melodic minor': 'Minore melodica',
    'Major pentatonic': 'Pentatonica maggiore',
    'Minor pentatonic': 'Pentatonica minore',
    'Minor blues': 'Blues minore',
    'Major blues': 'Blues maggiore',
    'Dorian': 'Dorica',
    'Phrygian': 'Frigia',
    'Lydian': 'Lidia',
    'Mixolydian': 'Misolidia',
    'Locrian': 'Locria',
    'Phrygian dominant': 'Frigia dominante',
    # --- music_theory: tunings
    'Standard (E A D G B E)': 'Standard (E A D G B E)',
    'Drop D (D A D G B E)': 'Drop D (D A D G B E)',
    'Half step down (E♭)': 'Mezzo tono sotto (E♭)',
    'DADGAD': 'DADGAD',
    'Open G (D G D G B D)': 'Open G (D G D G B D)',
    'Open D (D A D F# A D)': 'Open D (D A D F# A D)',
}
