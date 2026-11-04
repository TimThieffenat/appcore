"""Traduction des textes du socle : français (voir appcore/i18n.py).

Clé : le texte anglais du code ; valeur : sa traduction (un pluriel :
(singulier, pluriel)). Les champs {nom} doivent rester tels quels. Les textes
propres à une app sont dans le locales/ de l'app. Après un changement de
texte : python appcore/tools/i18n_check.py --core."""
# ruff: noqa: E501

T = {
    # --- appcore/boot.py
    '{app} could not start': "{app} n'a pas pu démarrer",
    '{app} stopped last time': "{app} s'est arrêtée la dernière fois",
    # --- appcore/crash_report.py
    'Send by email opens your email app with this report, addressed to {email}. Nothing is sent until you press Send.': "« Envoyer par e-mail » ouvre votre app d'e-mail avec ce rapport, adressé à {email}. Rien n'est envoyé tant que vous n'appuyez pas sur Envoyer.",
    'Send by email': 'Envoyer par e-mail',
    'Copy': 'Copier',
    'Close': 'Fermer',
    'What were you doing when the problem happened? (optional)': 'Que faisiez-vous quand le problème est arrivé ? (facultatif)',
    'Clear': 'Effacer',
    'Erase the errors and the log (after sending them)': 'Efface les erreurs et le journal (une fois envoyés)',
    'Copied.': 'Copié.',
    'Cleared.': 'Effacé.',
    'Your email app opens. The report is also copied, in case it is cut.': "Votre app d'e-mail s'ouvre. Le rapport est aussi copié, au cas où il serait coupé.",
    'No email app found. The report is copied: paste it in an email to {email}.': "Aucune app d'e-mail trouvée. Le rapport est copié : collez-le dans un e-mail à {email}.",
    # --- appcore/music_theory.py
    'Letters (C D E)': 'Lettres (C D E)',
    '{root} {scale}': '{root} {scale}',
    '{root} {mode}': '{root} {mode}',
    'Solfège ({notes})': 'Solfège ({notes})',
    'major': 'majeur',
    'minor': 'mineur',
    # --- appcore/page_settings.py
    'Instrument': 'Instrument',
    'Same as phone': 'Comme le téléphone',
    'Light (pastel)': 'Clair (pastel)',
    'Dark (neon)': 'Sombre (néon)',
    'Guitars: FluidR3_GM by Frank Wen (CC BY 3.0) · Symbols: DejaVu Sans (Bitstream Vera license)': 'Guitares : FluidR3_GM de Frank Wen (CC BY 3.0) · Symboles : DejaVu Sans (licence Bitstream Vera)',
    'Settings': 'Réglages',
    'Same as phone ({language})': 'Comme le téléphone ({language})',
    'Language': 'Langue',
    'Theme': 'Thème',
    'Note names': 'Noms des notes',
    'Show': 'Afficher',
    'What went wrong and what the app did, to send by email if the app misbehaves': "Ce qui s'est mal passé et ce que l'app a fait, à envoyer par e-mail si l'app se comporte mal",
    'Error report': "Rapport d'erreur",
    # --- instruments
    'Steel-string acoustic': 'Folk à cordes acier',
    'Nylon-string (classical)': 'Cordes nylon (classique)',
    'Soft keys (all musicians)': 'Clavier doux (tous instruments)',
    # --- music_theory: chords
    'Major': 'Majeur',
    'Minor': 'Mineur',
    'Diminished': 'Diminué',
    'Augmented': 'Augmenté',
    'Sus2': 'Sus2',
    'Sus4': 'Sus4',
    '6': '6',
    'Minor 6': 'Mineur 6',
    '7 (dominant)': '7 (dominante)',
    'Major 7': 'Majeur 7',
    'Minor 7': 'Mineur 7',
    'Half-diminished (m7♭5)': 'Demi-diminué (m7♭5)',
    'Diminished 7': '7 diminuée',
    'Minor-major 7': 'Mineur-majeur 7',
    '7sus4': '7sus4',
    'add9': 'add9',
    '9': '9',
    'Major 9': 'Majeur 9',
    'Minor 9': 'Mineur 9',
    # --- music_theory: modes
    'Scale': 'Gamme',
    'Chord': 'Accord',
    # --- music_theory: scales
    'Major (Ionian)': 'Majeure (ionien)',
    'Natural minor (Aeolian)': 'Mineure naturelle (éolien)',
    'Harmonic minor': 'Mineure harmonique',
    'Melodic minor': 'Mineure mélodique',
    'Major pentatonic': 'Pentatonique majeure',
    'Minor pentatonic': 'Pentatonique mineure',
    'Minor blues': 'Blues mineur',
    'Major blues': 'Blues majeur',
    'Dorian': 'Dorien',
    'Phrygian': 'Phrygien',
    'Lydian': 'Lydien',
    'Mixolydian': 'Mixolydien',
    'Locrian': 'Locrien',
    'Phrygian dominant': 'Phrygien dominant',
    # --- music_theory: tunings
    'Standard (E A D G B E)': 'Standard (E A D G B E)',
    'Drop D (D A D G B E)': 'Drop D (D A D G B E)',
    'Half step down (E♭)': 'Un demi-ton plus bas (E♭)',
    'DADGAD': 'DADGAD',
    'Open G (D G D G B D)': 'Open G (D G D G B D)',
    'Open D (D A D F# A D)': 'Open D (D A D F# A D)',
}
