import sys
import pytest
import pydicom
from pydicom.uid import generate_uid

from pathlib import Path

niffler_modules_path = Path.cwd() / 'modules'
dicom_anon_path = niffler_modules_path / 'dicom_anonymization'
sys.path.append(str(dicom_anon_path))
import DicomAnonymizer as DCMAnon
import DicomAnonymizer2 as DCMAnon2


class Config(object):
    """
    Config Object for dicom_anonymization tests
    """
    input_dir = pytest.data_dir / 'dicom_anonymization' / 'input'

    def __init__(self):
        pytest.create_dirs(
            self.input_dir
        )


# Initialize config object
test_config = Config()


class TestRandomizeID:
    """
    Test for DicomAnonymizer.randomizeID
    """

    def test_success(self):
        """
        Checks whether randomized img id starts with initial part of orig id.
        randomizeID() is deprecated so the call must emit a DeprecationWarning.
        """
        tmp_id = "45365768335.0.7486.131"
        start_str = tmp_id.split(".")[0]
        with pytest.deprecated_call():
            randId = DCMAnon.randomizeID(tmp_id)
        assert randId.startswith(start_str)


class TestAnonSample:
    """
    Tests for DicomAnonymizer.anonSample
    """

    def test_success_randomize(self):
        """
        Checks that anonSample returns a fresh UID (not derived from the original).
        UIDs are now generated via pydicom.uid.generate_uid() for full DICOM compliance.
        """

        id_type = "some_type"
        tmp_id = "45365768335.0.7486.131"
        tmp_file = {id_type: pytest.Dict2Class({'value': tmp_id})}
        anon_id = DCMAnon.anonSample(tmp_file, id_type, {})

        assert anon_id != tmp_id   # must differ from the original
        assert len(anon_id) > 0    # must be non-empty

    def test_success_no_randomize(self):
        """
        Checks whether anonymized img id starts with initial part of orig id.
        Test for if conditional
        Refer to DCMAnon.anonSample code.
        """
        id_type = "some_type"
        tmp_id = "45365768335.30.854.131"
        start_str = tmp_id.split(".")[0]
        tmp_file = {id_type: pytest.Dict2Class({'value': tmp_id})}
        anon_id = DCMAnon.anonSample(
            tmp_file, id_type, {tmp_id: '45365768335.0.7486.131'})

        assert anon_id.startswith(start_str)


class TestGetDcmFolders:
    """
    Tests for DicomAnonymizer.get_dcm_folders
    """

    def test_no_files(self):
        """
        Checks whether get_dcm_folders returns 0 folders
        """
        dcm_flds = DCMAnon.get_dcm_folders(
            test_config.input_dir / 'dcm_empty_dir')
        assert len(dcm_flds) == 0

    def test_get_folder(self):
        """
        Checks whether get_dcm_folders returns non 0 length of folders
        """
        dcm_flds = DCMAnon.get_dcm_folders(
            test_config.input_dir / 'dcm_root_dir')
        assert len(dcm_flds) != 0


# ---------------------------------------------------------------------------
# DicomAnonymizer2 tests
# ---------------------------------------------------------------------------

class TestAnonSampleV2:
    """Tests for DicomAnonymizer2.anonSample — UID generation and PatientID handling."""

    def test_uid_is_fresh_not_derived_from_original(self):
        """Non-PatientID UIDs must be fresh DICOM UIDs, not mutations of the original."""
        id_type = "StudyInstanceUID"
        tmp_id = "1.2.840.10008.5.1.4.1.1.2"
        tmp_file = {id_type: pytest.Dict2Class({'value': tmp_id})}
        anon_id = DCMAnon2.anonSample(tmp_file, id_type, {})
        assert anon_id != tmp_id
        assert len(anon_id) > 0

    def test_patient_id_uses_random_string(self):
        """PatientID must be anonymized to a 25-char alphanumeric string."""
        id_type = "PatientID"
        tmp_id = "P001"
        tmp_file = {id_type: pytest.Dict2Class({'value': tmp_id})}
        anon_id = DCMAnon2.anonSample(tmp_file, id_type, {})
        assert anon_id != tmp_id
        assert len(anon_id) == 25

    def test_cached_id_returned_on_repeat(self):
        """Calling anonSample twice with the same original ID must return the same replacement."""
        id_type = "StudyInstanceUID"
        tmp_id = "1.2.3.4.5"
        tmp_file = {id_type: pytest.Dict2Class({'value': tmp_id})}
        uid_dict = {}
        first = DCMAnon2.anonSample(tmp_file, id_type, uid_dict)
        second = DCMAnon2.anonSample(tmp_file, id_type, uid_dict)
        assert first == second


# ---------------------------------------------------------------------------
# _stamp_deidentified tests (DicomAnonymizer v1 and v2)
# ---------------------------------------------------------------------------

class TestStampDeidentified:
    """Tests for _stamp_deidentified in both DicomAnonymizer versions."""

    @pytest.mark.parametrize("mod", [DCMAnon, DCMAnon2])
    def test_patient_identity_removed(self, mod):
        ds = pydicom.Dataset()
        mod._stamp_deidentified(ds)
        assert ds.PatientIdentityRemoved == "YES"

    @pytest.mark.parametrize("mod", [DCMAnon, DCMAnon2])
    def test_default_deidentification_method(self, mod):
        ds = pydicom.Dataset()
        mod._stamp_deidentified(ds)
        assert ds.DeidentificationMethod == "Niffler Basic Profile"

    @pytest.mark.parametrize("mod", [DCMAnon, DCMAnon2])
    def test_custom_deidentification_method(self, mod):
        ds = pydicom.Dataset()
        mod._stamp_deidentified(ds, method="Custom Profile")
        assert ds.DeidentificationMethod == "Custom Profile"
