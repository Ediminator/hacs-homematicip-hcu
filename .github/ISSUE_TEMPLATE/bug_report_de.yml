name: Bug melden
description: Einen Fehler oder ein unerwartetes Verhalten melden
body:
  - type: markdown
    attributes:
      value: |
        Dieses Formular ist **ausschließlich für Bug-Reports** gedacht.

        Bitte nutze dieses Formular nicht für Fragen oder Feature-Wünsche.
        Stelle sicher, dass **alle erforderlichen Informationen** angegeben sind,
        damit das Problem sinnvoll analysiert werden kann.

        ⚠️ **WICHTIG**
        Sinnvolle Unterstützung ist nur möglich, wenn alle erforderlichen Informationen
        bereitgestellt werden – insbesondere **Diagnosedaten** und **Logdateien**.
        Issues ohne diese Informationen können kommentarlos geschlossen werden.

        Bitte lies alle Punkte sorgfältig durch und fülle das Formular vollständig aus.

  - type: checkboxes
    attributes:
      label: Bestätigung
      options:
        - label: Ich habe unter **„Good first issues“** geprüft, ob dieses Problem bereits gemeldet oder behoben wurde.
          required: true
        - label: Ich habe das **README gelesen** und alle relevanten Anweisungen befolgt.
          required: true

  - type: textarea
    validations:
      required: true
    attributes:
      label: Problembeschreibung
      description: |
        Bitte beschreibe das Problem so genau wie möglich und beantworte dabei folgende Fragen:

        1. Was passiert aktuell?
        2. Wann und wie tritt das Problem auf?
        3. Was hast du erwartet, dass passiert?
        4. Was hast du bereits versucht?

        **Keine Logs hier einfügen!** Screenshots sind willkommen.

  - type: markdown
    attributes:
      value: |
        ## Umgebung

  - type: input
    validations:
      required: true
    attributes:
      label: Betroffene Integrationsversion
      placeholder: x.y.z
      description: |
        Gib die Version der Integration an, bei der das Problem auftritt.

  - type: input
    attributes:
      label: Letzte funktionierende Integrationsversion
      placeholder: x.y.z
      description: |
        Falls bekannt, andernfalls leer lassen.

  - type: markdown
    attributes:
      value: |
        ## Details

  - type: textarea
    attributes:
      label: Diagnosedatei (erforderlich)
      placeholder: "Diagnose-.json-Datei hier per Drag-and-drop hochladen."
      description: |
        ⚠️ **WICHTIG**
        Lade die Diagnosedatei **ausschließlich als Datei** per Drag-and-drop hoch.

        **Keine Logs oder Textinhalte hier einfügen.**

        Dieses Feld nur überspringen, wenn sich das Problem auf die Erstinstallation bezieht.

  - type: textarea
    attributes:
      label: Logdatei (erforderlich)
      placeholder: "Logdatei hier per Drag-and-drop hochladen."
      description: |
        Bitte lade die relevante Logdatei hoch.
        Logs auf **DEBUG-Level** werden dringend empfohlen.

        Stelle sicher, dass das Log den Zeitraum des Problems abdeckt
        und keine sensiblen Daten enthält.

  - type: textarea
    attributes:
      label: Zusätzliche Informationen
      description: |
        Füge hier weitere Informationen hinzu, z. B. Hinweise zur Reproduktion,
        Screenshots oder sonstige relevante Details.