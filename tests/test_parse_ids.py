import io
import json

from ontobio.io import assocparser
from ontobio.io import gafparser

from ontobio.io import assocwriter

def test_no_colon_in_id():
    parser = gafparser.GafParser()
    valid = parser._validate_id("FOOBAR", assocparser.SplitLine("", [""] * 17, "taxon:foo"))

    assert not valid
    assert len(parser.report.messages) == 1
    assert parser.report.messages[0]["level"] == assocparser.Report.ERROR

def test_empty_id():
    parser = gafparser.GafParser()
    valid = parser._validate_id("", assocparser.SplitLine("", [""] * 17, "taxon:foo"))
    assert not valid
    assert len(parser.report.messages) == 1
    assert parser.report.messages[0]["level"] == assocparser.Report.ERROR

def test_pipe_in_id():
    parser = gafparser.GafParser()
    valid = parser._validate_id("F|OO:123", assocparser.SplitLine("", [""] * 17, "taxon:foo"))

    assert not valid
    assert len(parser.report.messages) == 1
    assert parser.report.messages[0]["level"] == assocparser.Report.ERROR

def test_bad_character_in_id():
    parser = gafparser.GafParser()
    valid = parser._validate_id("FOO:1&23", assocparser.SplitLine("", [""] * 17, "taxon:foo"))

    assert not valid
    assert len(parser.report.messages) == 1
    assert parser.report.messages[0]["level"] == assocparser.Report.ERROR

def test_empty_post_colon():
    parser = gafparser.GafParser()
    valid = parser._validate_id("FOO:", assocparser.SplitLine("", [""] * 17, "taxon:foo"))

    assert not valid
    assert len(parser.report.messages) == 1
    assert parser.report.messages[0]["level"] == assocparser.Report.ERROR

def test_empty_pre_colon():
    parser = gafparser.GafParser()
    valid = parser._validate_id(":123", assocparser.SplitLine("", [""] * 17, "taxon:foo"))

    assert not valid
    assert len(parser.report.messages) == 1
    assert parser.report.messages[0]["level"] == assocparser.Report.ERROR

def test_validate_with_allowed_ids():
    parser = gafparser.GafParser()
    valid = parser._validate_id("FOO:123", assocparser.SplitLine("", [""]*17, "taxon:foo"), allowed_ids=["FOO"])
    assert valid

def test_validate_with_disallowed_id():
    parser = gafparser.GafParser()
    valid = parser._validate_id("FOO:123", assocparser.SplitLine("", [""]*17, "taxon:foo"), allowed_ids=["BAR"])
    assert len(parser.report.messages) == 1
    assert parser.report.messages[0]["level"] == assocparser.Report.WARNING

def test_validate_pipe_separated():
    parser = gafparser.GafParser()
    ids = parser.validate_pipe_separated_ids("PMID:12345", assocparser.SplitLine("", [""] * 17, "taxon:foo"))
    assert set(ids) == set(["PMID:12345"])

    ids = parser.validate_pipe_separated_ids("PMID:12345|PMID:11111", assocparser.SplitLine("", [""] * 17, "taxon:foo"))
    assert set(ids) == set(["PMID:12345", "PMID:11111"])

def test_validate_pipe_separated_with_bad_ids():
    parser = gafparser.GafParser()
    ids = parser.validate_pipe_separated_ids("PMID:123[2]|PMID:11111", assocparser.SplitLine("", [""] * 17, "taxon:foo"))

    assert ids == None

    ids = parser.validate_pipe_separated_ids("PMID:123[2]", assocparser.SplitLine("", [""] * 17, "taxon:foo"))
    assert ids == None

def test_validate_pipe_separated_empty_allowed():
    parser = gafparser.GafParser()
    ids = parser.validate_pipe_separated_ids("", assocparser.SplitLine("", [""] * 17, "taxon:foo"), empty_allowed=True)

    assert ids == []

def test_validate_pipe_with_additional_delims():
    parser = gafparser.GafParser()
    ids = parser.validate_pipe_separated_ids("F:123,B:234|B:111", assocparser.SplitLine("", [""] * 17, "taxon:foo"), extra_delims=",")

    assert set(ids) == set(["F:123", "B:234", "B:111"])

    result = parser.parse_line("PomBase\tSPAC25B8.17\typf1\t\tGO:1990578\tGO_REF:0000024\tISO\tUniProtKB:Q9CXD9|ensembl:ENSMUSP00000038569,PMID:11111\tC\tintramembrane aspartyl protease of the perinuclear ER membrane Ypf1 (predicted)\tppp81\tprotein\ttaxon:4896\t20150305\tPomBase\t\t")
    assert set(result.associations[0]["evidence"]["with_support_from"]) == set(["UniProtKB:Q9CXD9", "ensembl:ENSMUSP00000038569", "PMID:11111"])

def test_doi_id():
    parser = gafparser.GafParser()
    valid = parser._validate_id("DOI:10.1007/BF00127499", assocparser.SplitLine("", [""]*17, "taxon:foo"))
    assert valid

def test_validate_references():
    parser = gafparser.GafParser()
    valid = parser.validate_references(["MGI:12345", "PMID:23456"], assocparser.SplitLine("", [""]*17, "taxon:foo"))
    assert valid

def test_validate_references_same_prefix():
    parser = gafparser.GafParser()
    valid = parser.validate_references(["MGI:123", "MGI:234"], assocparser.SplitLine("", [""]*17, "taxon:foo"))
    assert len(parser.report.messages) == 1
    assert parser.report.messages[0]["type"] == assocparser.Report.INVALID_REFERENCES
    assert not valid

def test_normalize_refs_single_bad_ref():
    parser = gafparser.GafParser()
    ref = parser.normalize_refs(["FB:123"], assocparser.SplitLine("", [""]*17, "taxon:foo"))
    assert ref == ["FB:123"]
    assert len(parser.report.messages) == 1
    assert parser.report.messages[0]["type"] == assocparser.Report.INVALID_IDSPACE

def test_normalize_refs_many_bad_refs():
    parser = gafparser.GafParser()
    refs = parser.normalize_refs(["FB:123", "FB:234"], assocparser.SplitLine("", [""]*17, "taxon:foo"))
    assert refs == ["FB:123", "FB:234"]
    assert len(parser.report.messages) == 1
    assert parser.report.messages[0]["type"] == assocparser.Report.INVALID_IDSPACE

def test_normalize_refs_good_and_bad_refs():
    parser = gafparser.GafParser()
    refs = parser.normalize_refs(["FB:123", "PMID:234"], assocparser.SplitLine("", [""]*17, "taxon:foo"))
    assert len(parser.report.messages) == 1
    assert parser.report.messages[0]["type"] == assocparser.Report.INVALID_IDSPACE

def test_normalize_refs_good():
    parser = gafparser.GafParser()
    refs = parser.normalize_refs(["PMID:123"], assocparser.SplitLine("", [""]*17, "taxon:foo"))
    assert refs == ["PMID:123"]
