//! End-to-end tests for ToUnicode CMap.
//!
//! Builds a synthetic PDF with a Type1 font that has a /ToUnicode
//! stream mapping an Identity Latin-1 source to Unicode and verifies
//! that text extraction goes through the CMap.

use pdf_analysis::ToUnicodeCMap;

#[test]
fn cmap_decodes_basic_bfchar() {
    let cmap_text = b"\
1 begincodespacerange\n<00> <FF>\nendcodespacerange\n\
3 beginbfchar\n\
<41> <0041>\n\
<42> <0042>\n\
<43> <0043>\n\
endbfchar\n";
    let m = ToUnicodeCMap::parse(cmap_text);
    assert_eq!(m.decode_bytes(b"\x41\x42\x43"), "ABC");
    assert_eq!(m.source_byte_width, 1);
}

#[test]
fn cmap_decodes_bfrange_with_array() {
    let cmap_text = b"\
1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n\
1 beginbfrange\n\
<0010> <0012> [<0030> <0031> <0032>]\n\
endbfrange\n";
    let m = ToUnicodeCMap::parse(cmap_text);
    assert_eq!(m.decode_bytes(&[0x00, 0x10]), "0");
    assert_eq!(m.decode_bytes(&[0x00, 0x11]), "1");
    assert_eq!(m.decode_bytes(&[0x00, 0x12]), "2");
}
