# Portable body fonts

Charis 7.000: https://software.sil.org/downloads/r/charis/Charis-7.000.zip
Source and documentation: https://software.sil.org/charis/download/
License: charis/OFL.txt (SIL Open Font License).

XCharter 1.26: https://ctan.math.illinois.edu/fonts/xcharter/opentype/
License and attribution: xcharter/README (Bitstream free-font license).

Install the selected family before rendering (on macOS, copy its font files into ~/Library/Fonts). The builder uses the family name; it does not install fonts automatically. The selected XCharter default uses 11pt body, 1.08 line spacing and 0.9in margins. The Charis diagnostic alternative uses 10.5pt / 1.05 / 0.9in. Different font metrics change pagination.

Build using the dependencies in report/BUILD.md, then add --paragraph-layout balanced-xcharter --pdfa, or --paragraph-layout balanced-charis --pdfa. PDF/A export requests LibreOffice PDF/A-2b; this is not an independent conformance certification.
