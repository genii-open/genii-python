"""
Read .eeg files (Compumedics Profusion files) obtained from the database of UMMC
"""

#    You can redistribute this script and/or modify it under the terms of the
#    GNU General Public License as published by the Free Software Foundation,
#    either version 3 of the License, or (at your option) any later version.
#
#    This script is provided AS-IS and WITHOUT ANY WARRANTY; without even the
#    implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
#    See the GNU General Public License <http://www.gnu.org/licenses/> for
#    more details.

import struct
import numpy as np
import os
import os.path as op
import re
from xml.etree import ElementTree as ET
from dataclasses import dataclass
from typing import Tuple, Iterable, Dict, DefaultDict, Any
from io import BufferedReader
from glob import glob
from access_parser import AccessParser
import mne
import ctypes

# Pre compile for efficiency
_data_root_re_ptrn = re.compile("EEGData", re.IGNORECASE)
_hdr_re_ptrn = re.compile("EEGData.ini", re.IGNORECASE)
_elt_plcm_root_re_ptrn = re.compile("ElectrodePlacements", re.IGNORECASE)
_ev_re_ptrn = re.compile("EEGStudyDB.mdb", re.IGNORECASE)

# Disable debug message
def debug(*_, **__):
    pass

# Constants
# _inter1020 = ("Fp1", "Fp2", "F3", "F4", "F7", "F8", "C3", "C4", "T3", "T4", "P3", "P4", "T5", "T6", "O1", "O2", "A1", "A2", "Fz", "Cz", "Pz")
_common_other_ch = ("emg", "eog", "ecg")
_head_rad = 0.12

@dataclass
class CompumedicHeader():
    ch_names: Tuple[str, ...]
    n_channels: int
    sampling_freq: float

@dataclass
class EegHeader():
    n_samples_per_rda: int
    n_channels: int

@dataclass
class RdaSegment():
    magic: int
    first_sample: int
    n_samples: int
    is_closed: bool
    shape: Tuple[int, int]
    _data: np.ndarray | None

@dataclass
class Rda():
    name: str
    sealed: bool
    pdel: int
    _file: BufferedReader
    _sgmt_pos: Tuple[int, ...]
    _sgmt: Tuple[RdaSegment, ...]

    def __getitem__(self, idx: int) -> np.ndarray:
        if type(idx) is not int:
            raise ValueError()
        sgmt = self._sgmt[idx]
        if sgmt._data is None:
            self._file.seek(self._sgmt_pos[idx])
            count = sgmt.shape[0] * sgmt.shape[1]
            # TODO this does not check for truncated segment, use struct and magic number to check is better
            sgmt._data = np.fromfile(self._file, dtype="<f4", count=count).reshape(sgmt.n_samples, -1).transpose()
            
            if sgmt._data.size != count:
                raise "Data truncated"
        return sgmt._data
    
    def __call__(self, idx: int) -> RdaSegment:
        if type(idx) is not int:
            raise ValueError()
        return self._sgmt[idx]
    
    def __len__(self) -> int:
        return len(self._sgmt_pos)

    def __del__(self):
        self._file.close()

@dataclass
class ElectrodePlacement():
    name: str
    ch_pos: np.ndarray
    ch_names: Tuple[str, ...]

@dataclass
class Event():
    event_id: int
    event_type_id: int
    event_category_id: int
    event_kind_id: int
    start_sec: float
    duration_sec: float
    event_name: str

@dataclass
class EventCategory():
    category_id: int
    category_name: str
    category_desc: str

def _case_insensitive_path_join(root: str, dir_re_ptrn: re.Pattern, err_on_fail=True) -> str:
    try:
        return op.join(
            root, 
            next(
                filter(
                    dir_re_ptrn.search,
                    os.listdir(root)
                )
            )
        )
    except StopIteration:
        if err_on_fail:
            raise f"No directory in '{root}' matches '{dir_re_ptrn.pattern}'"
        else:
            return None

class Compumedics():
    """
    A exported Compumedics folder 
    """


    def __init__(self, path: str, skip_consistency_check = True) -> None:
        """
        Load an exported Compumedics folder

        path: str
            The path to an .eeg, .sdy or .rda file
            If .rda is provided, only that one file will be imported
            Note that .rda depends on metadata from other files, so they are not openable after being moved out of its original place
        
        skip_consistency_check: bool = True
            Skip consistency checking among headers, should be fine to skip 
        """

        path = op.abspath(path)
        debug("Start to import", path)

        debug("Checking necessary files...")
        eeg_path, sdy_path, hdr_path, rda_paths = self._check_compulsary_paths(path)
        debug("Checking optional files...")
        elt_plcm_paths, ev_path = self._check_optional_paths(eeg_path)

        debug("Reading Compumedics header (.sdy) file")
        self.compumedics_header: CompumedicHeader = self._read_cpmd_hdr(sdy_path)
        debug("Compumedics header file ok")
        
        debug("Reading EEG header (eegdata.ini) file...")
        self.eeg_header: EegHeader = self._read_eeg_hdr(hdr_path)
        debug("EEG header file ok")

        if skip_consistency_check:
            debug("Consistency check is skipped")
        else:
            debug("Checking consistency...")
            self._check_consistency()
            debug("Headers consistency ok")

        debug("Reading .rda file(s)...")
        self.rda: Tuple[Rda, ...] = tuple(map(self._read_rda_hdr, rda_paths))
        debug(".rda files loaded lazily")
        
        if len(elt_plcm_paths) > 0:
            debug("Reading electrode placement file(s)...")
            self.electrode_placements: Tuple[ElectrodePlacement] = tuple(
                filter(
                    lambda e: e is not None, 
                    map(self._read_elt_plcm, elt_plcm_paths)
                )
            )

            debug("Electrode placement file(s) done")

        if ev_path is not None:
            debug("Reading event database...")
            self.events, self.event_category, self.event_kind = self._parse_event(ev_path)
            debug("Event database done")

        debug("Import complete")
        
    def export_to_mne_raw(self, link_event: bool | Iterable[int] = True, link_elt_plcm: bool | int | str = "standard_1020", pad_zero: bool = False):
        """
        Export the read data to a MNE RawArray object
        
        link_event: bool | Iterable[int] = True
            Mark the exported RawArray with data in the event database
            If True but no database found, error
            If Iterable[int], only event with the provided category id will be linked

        link_elt_plcm: bool | int | str = "standard_1020"
            Set the electrode placement (a.k.a. montage) of the exported RawArray object
            If False, no electrode placement will be set
            If True, and only one electrode placement file was loaded, the file will be used, otherwise error
            If int, the file with the index will be used
            If str, MNE builtin montages will be used

        pad_zero: bool = False
            Pad zeros when the first sample of a segment does not line up with the last sample of previous segment
        """
        def check_channel_belongs_to_montage(ch_name: str, montage: mne.channels.DigMontage | None):
            if montage is None:
                return False
            else:
                return ch_name in montage.ch_names

        debug("Converting Compumedics files into MNE objects")
        debug("Loading all .rda segments...")
        all_sgmt_ndarr = self._merge_all_rda_sgmt(pad_zero=pad_zero)
        debug("Loaded .rda segments, shape =", all_sgmt_ndarr.shape)

        ch_types = []

        debug("Attempting to link electrode placement file")
        montage = None
        link_elt_plcm_type = type(link_elt_plcm)
        if link_elt_plcm_type is bool:
            if link_elt_plcm:
                match len(self.electrode_placements):
                    case 1:
                        debug("Linking the only electrode placement file...")
                        montage = self._make_dig_montage()
                    case 0:
                        raise "No electrode placement file was loaded"
                    case _:
                        raise "Multiple electrode placement files was loaded"
            else:
                debug("Not linking any electrode placement file")
        elif link_elt_plcm_type is int:
            debug(f"Linking electrode placement file with index {link_elt_plcm}")
            montage = self._make_dig_montage(link_elt_plcm)
        else:
            debug(f"Making standard digital montage ({link_elt_plcm})")
            montage = mne.channels.make_standard_montage(link_elt_plcm)
        debug("Digital montage ok")

        debug("Deducting channel types...")
        for ch_name in self.compumedics_header.ch_names:
            ch_prefix = ch_name[:3].lower()
            if ch_prefix in _common_other_ch:
                ch_types.append(ch_prefix)
            elif check_channel_belongs_to_montage(ch_name, montage):
                ch_types.append("eeg")
            elif check_channel_belongs_to_montage(ch_name.split("-")[0].strip(), montage):
                debug(f"WARNING: Channel {ch_name} seems to be a referenced channel")
                ch_types.append("eeg")
            else:
                debug(f"WARNING: Cannot deduct the channel type of {ch_name}, it is set to 'misc' type")
                ch_types.append("misc")
        debug("Channel type deduction complete")

        debug("Linking events...")
        event_ndarr = None
        if type(link_event) is bool:
            if link_event:
                debug(f"All {len(self.events)} event(s) will be linked")
                event_ndarr = self._make_event_ndarr(self.events)
            else:
                debug("Not linking event")
        elif isinstance(link_event, Iterable):
            debug("Only events that belongs to the following category will be linked:", link_event)
            debug("Category name:", [cat.category_name for cat in self.event_category])
            rel_ev = tuple(filter(lambda e: e.event_category_id in link_event, self.events))
            debug(f"Linking {len(rel_ev)} event(s)")
            event_ndarr = self._make_event_ndarr(rel_ev)
        debug("Event processing ok")

        debug("Constructing MNE objects...")
        mne_info = mne.create_info(
            ch_names=self.compumedics_header.ch_names,
            sfreq=self.compumedics_header.sampling_freq,
            ch_types=ch_types
        )
        debug("Info:", mne_info)

        ann = None
        if event_ndarr is not None:
            ann = mne.annotations_from_events(
                event_ndarr,
                self.compumedics_header.sampling_freq,
                event_desc=lambda eid: self.event_kind[eid]
            )
        debug("Annotation:", ann)

        raw = mne.io.RawArray(
            data=all_sgmt_ndarr,
            info=mne_info
        )

        mne.add_reference_channels(raw, "ref")
        raw.set_montage(montage)
        if ann is not None:
            raw.set_annotations(ann)
        debug("Raw:", raw)
        
        debug("Conversion complete")

        return raw

    def _check_compulsary_paths(self, path: str) -> Tuple[str, str, str, Tuple[str, ...]]:
        path_adjusted = True
        is_opening_rda = False

        eeg_path = None
        sdy_path = None
        data_root = None
        hdr_path = None
        rda_paths = []

        match path[-4:]:
            case ".eeg":
                eeg_path = op.dirname(sorted(glob(op.join(path, "**","*.sdy")))[0])
                path_adjusted = False
            case ".sdy":
                eeg_path = op.dirname(path)
            case ".rda":
                eeg_path = op.dirname(op.dirname(path))
                is_opening_rda = True

        if path_adjusted:
            debug("Adjusted root path to", eeg_path)

        sdy_path = sorted(glob(op.join(eeg_path, "*.sdy")))[0]
        debug("Found .sdy at", sdy_path)
        
        data_root = _case_insensitive_path_join(eeg_path, _data_root_re_ptrn)
        debug("Checking the content of", data_root)

        hdr_path = _case_insensitive_path_join(data_root, _hdr_re_ptrn)
        debug("Found EEG header at", hdr_path)
        
        if is_opening_rda:
            rda_paths = [path]
            debug("Only open the given .rda file:", path)
        else:
            rda_paths = sorted(tuple(glob(op.join(data_root, "*.rda"))))
            debug(f"Opening all ({len(rda_paths)}) .rda file(s)")
        
        if len(rda_paths) == 0:
            raise "No .rda file to import"

        return eeg_path, sdy_path, hdr_path, rda_paths

    def _check_optional_paths(self, eeg_path: str) -> Tuple[Tuple[str, ...], str]:
        elt_plcm_paths = sorted(tuple(glob(op.join(_case_insensitive_path_join(eeg_path, _elt_plcm_root_re_ptrn), "*.xml"))))
        debug("Checking electrode placement file...")
        if len(elt_plcm_paths) == 0:
            debug("WARNING: No electrode placement file found")
        elif len(elt_plcm_paths) > 1:
            debug("WARNING: Multiple electrode palcement files found")
        else:
            debug("Electrode placement file ok")
        ev_path = _case_insensitive_path_join(eeg_path, _ev_re_ptrn, err_on_fail=False)
        debug("Checking event database...")
        if ev_path is None:
            debug("WARNING: No event database found")
        else:
            debug("Event database ok")
        return elt_plcm_paths, ev_path

    def _read_cpmd_hdr(self, sdy_path: str) -> CompumedicHeader:
        hdr = ET.parse(sdy_path)
        debug("Compumedics header loaded")
        
        ch_names = [ch.get("name") for ch in hdr.iter("Channel")]
        n_ch = len(ch_names)
        debug(f"{n_ch} channel(s):", ch_names)

        s_freq = float(next(hdr.iter("Study")).get("eeg_sample_rate"))
        debug(f"Sampling frequency: {s_freq}Hz")

        return CompumedicHeader(
            ch_names=ch_names,
            n_channels=n_ch,
            sampling_freq=s_freq
        )

    def _read_eeg_hdr(self, hdr_path: str):
        with open(hdr_path, "r") as file:
            debug("EEG header file loaded")
            
            n_samples = None
            n_channels = None
            for line in file:
                line = line.split("=")
                if len(line) < 2:
                    continue
                line = tuple(map(str.strip, line))
                if line[0] == "Integral space size in samples":
                    n_samples = int(line[1])
                elif line[0] == "Number of Channels":
                    n_channels = int(line[1])
            
            debug(f"Maximum {n_samples} samples for each .rda file")
            debug(f"{n_channels} channels in each .rda file")
            
            return EegHeader(n_samples_per_rda=n_samples, n_channels=n_channels)
    
    def _check_consistency(self):
        if self.compumedics_header.n_channels != self.eeg_header.n_channels:
            raise f"Number of channel does not match: {self.compumedics_header.n_channels} in .sdy and {self.eeg_header.n_channels} in EEGData.ini"

    # TODO this function assume the file encoding have sizeof(char) = 1, which may or may not be true universally 
    def _read_rda_hdr(self, rda_path: str):
        debug(f"Opening .rda file: {rda_path}")
        file = open(rda_path, "rb")
        sealed = struct.unpack_from("<?", file.read(1))[0]
        pdel = struct.unpack_from("<l", file.read(4))[0]
        # Unused
        file.seek(file.tell() + 95)

        debug("Reading .rda segments...")
        sgmt_pos, sgmt = self._read_all_rda_sgmt(file)
        debug(f"Read {len(sgmt)} segment(s), n_samples:", list(map(lambda s: s.n_samples, sgmt)))

        return Rda(
            name=op.basename(rda_path),
            sealed=sealed,
            pdel=pdel,
            _file=file,
            _sgmt_pos=sgmt_pos,
            _sgmt=sgmt
        )
        
    # after the end of the segment, -1L (the magic number) will appear, and then the first_sample, n_samples, closed, and 175 bytes of padding
    def _read_all_rda_sgmt(self, file: BufferedReader) -> Tuple[Tuple[int, ...], Tuple[RdaSegment, ...]]:
        sgmt_pos = []
        sgmt = []

        while file.peek(1) != b'':

            (magic, first_sample, n_samples, is_closed)  = struct.unpack_from("<qqq?", file.read(25))
            
            if n_samples > self.eeg_header.n_samples_per_rda:
                debug("WARNING: This .rda file have more sample than its header file suggested")
                debug(f"INFO: n_samples = {n_samples} in .rda but n_samples = {self.eeg_header.n_samples_per_rda} in EEGData.ini")

            # Start of data
            sgmt_pos.append(file.tell() + 175)

            shape = (self.eeg_header.n_channels, n_samples)

            sgmt.append(
                RdaSegment(
                    magic=magic,
                    first_sample=first_sample,
                    n_samples=n_samples,
                    is_closed=is_closed,
                    shape=shape,
                    _data=None
                )
            )
            
            # Skip to the magic number of next segment
            file.seek(file.tell() + 175 + n_samples * self.eeg_header.n_channels * 4)
        
        return sgmt_pos, sgmt

    def _read_elt_plcm(self, elt_plcm_path: str):
        try:
            debug("Reading electrode placement file:", elt_plcm_path)
            elt_plcm = ET.parse(elt_plcm_path)
            
            ch_names = []
            ch_pos = []

            for elt in elt_plcm.iter("Electrode"):
                label = elt.find("Label").text
                if label == "Trigger":
                    debug("Dropping location of channel 'Trigger' (Trigger channel)")
                elif label not in self.compumedics_header.ch_names:
                    debug(f"Dropping location of channel '{label}' (Not in .sdy)")
                else:
                    ch_names.append(label)
                    ch_pos.append(
                        (
                            float(elt.find("XCoordinate").text),
                            float(elt.find("YCoordinate").text)
                        )
                    )
            ch_pos = np.array(ch_pos)
            
            # Center on (0,0) and normalize
            ch_pos -= np.mean(ch_pos)
            # ch_pos = _head_rad * ch_pos / np.max(np.abs(ch_pos))
            #TODO normalize
            rad2 = np.sqrt(np.max(np.sum(np.square(ch_pos), axis=1)))
            ch_pos = _head_rad * ch_pos / rad2
            debug(f"Placement processing complete: {len(ch_names)} channels")

            return ElectrodePlacement(name=op.basename(elt_plcm_path), ch_pos=ch_pos, ch_names=ch_names)
        except Exception as e:
            debug("ERROR occured when processing electrode placement file(s):")
            debug(e)
            return None

    def _parse_event(self, ev_path: str) -> Tuple[Tuple[Event, ...], Tuple[EventCategory, ...], Dict[str | int, int | str]]:
        def parse_time(ev_table: DefaultDict[Any, list], col_common_name: str, row: int):
            hi = col_common_name + "Hi"
            lo = col_common_name + "Lo"
            return ((ev_table[hi][row] << 32) + ctypes.c_uint32(ev_table[lo][row]).value) / 1_000_000_000

        try:
            debug("Parsing event database", ev_path)
            db = AccessParser(ev_path)
            debug("Database parsing ok")

            debug("Processing EEGEvent")
            ev_table = db.parse_table("EEGEvent")
            ev = []
            # FIXME probably somewhere in the eventdb?
            ev_kind = {}
            for row in np.nditer(np.where(np.invert(np.array(ev_table["IsEndEvent"])))):
                ev_name = ev_table["EventString"][row]
                if ev_name not in ev_kind.keys():
                    ev_k_id = len(ev_kind)
                    ev_kind[ev_name] = ev_k_id
                    ev_kind[ev_k_id] = ev_name
                else:
                    ev_k_id = ev_kind[ev_name]
                ev.append(Event(
                    event_id=ev_table["EventID"][row],
                    event_type_id=ev_table["EventTypeID"][row],
                    event_category_id=ev_table["EventCategoryID"][row],
                    event_kind_id=ev_k_id,
                    start_sec=parse_time(ev_table, "StartSecond", row),
                    duration_sec=parse_time(ev_table, "Duration", row),
                    event_name=ev_table["EventString"][row]
                ))
            debug(f"Found {len(ev)} event(s), {len(ev_kind)} unique name(s)")

            debug("Processing EEGEventCategory")
            cat_table = db.parse_table("EEGEventCategory")
            cat = []
            for rid, cid in enumerate(cat_table["EventCategoryID"]):
                cat.append(
                    EventCategory(
                        category_id=cid,
                        category_name=cat_table["Name"][rid],
                        category_desc=cat_table["Description"][rid],
                    )
                )
            debug(f"Found {len(cat)} event categories")

            return tuple(ev), tuple(cat), ev_kind
        except Exception as e:
            debug("ERROR occured when processing event database:")
            debug(e)
            debug(e.args)
            return (), (), {}

    def _merge_all_rda_sgmt(self, pad_zero: bool) -> np.ndarray:
        all_sgmt = []
        n_sample_merged = 0
        for ridx, r in enumerate(self.rda):
            for sidx in range(len(r)):
                sgmt = r(sidx)
                sgmt_ndarr = r[sidx]
                if sgmt.first_sample > n_sample_merged and pad_zero:
                    debug(f"Padding 0s at time index [{n_sample_merged}, {sgmt.first_sample}]")
                    all_sgmt.append(
                        np.zeros(
                            (
                                self.compumedics_header.n_channels,
                                sgmt.first_sample - n_sample_merged
                            )
                        )
                    )
                    n_sample_merged = sgmt.first_sample
                all_sgmt.append(sgmt_ndarr)
                n_sample_merged += sgmt.n_samples
        return np.concatenate(all_sgmt, axis=1)

    def _make_dig_montage(self, idx=0):
        elt_plcm = self.electrode_placements[idx]
        debug("Processing electrode placement file", elt_plcm.name)

        rad2 = np.sum(np.square(elt_plcm.ch_pos), axis=1)
        sphere_rad_2 = np.max(rad2)
        debug(f"Head sphere radius {np.sqrt(sphere_rad_2)}m")

        debug("Fitting electrodes on head sphere...")
        ch_pos = np.concatenate(
            (
                self.electrode_placements[idx].ch_pos,
                np.sqrt(sphere_rad_2 - rad2).reshape(-1, 1)
            ),
            axis=1
        )
        ch_pos_dict = {}
        for i, ch_name in enumerate(elt_plcm.ch_names):
            ch_pos_dict[ch_name] = ch_pos[i]
        # TODO find nasion, lpa and rpa
        
        debug("Making digital head montage...")
        montage = mne.channels.make_dig_montage(
            ch_pos=ch_pos_dict,
            coord_frame="head"
        )
        debug("Digital montage:", montage)

        return montage
    
    def _make_event_ndarr(self, event: Tuple[Event]):
        # print(event)
        event_ndarr = np.zeros((len(event), 3))
        for eidx, ev in enumerate(event):
            event_ndarr[eidx][0] = ev.start_sec * self.compumedics_header.sampling_freq
            event_ndarr[eidx][2] = ev.event_kind_id
        return event_ndarr

if __name__ == "__main__":
    # c = Compumedics("ainudin\\data\\Export-#1430_2484_2023-11-20_14-28-18.eeg\\Export-#1430_2484_2023-11-20_14-28-18.sdy")
    # r = mne.io.read_raw("C:\\Users\\Puah Jia Hong\\Desktop\\gra\\patient\\ainudin\\data\\Ainudin.edf",encoding="latin1", preload=True)
    # link_event = [0, 1, 8, 9]

    # # c = Compumedics("TehYY.eeg-20240426T121115Z-001\\TehYY.eeg")
    # # r = mne.io.read_raw("Teh YY Pruned EDF.edf", encoding="latin1")
    # # link_event = [1]
    # print("\n\n\n")

    # print("Compumedic header:")
    # print(c.compumedics_header)
    # print("\n\n\n")

    # print("EEG header")
    # print(c.eeg_header)
    # print("\n\n\n")

    # print("Electrode placements:")
    # for idx, plcm in enumerate(c.electrode_placements):
    #     print(idx)
    #     print(plcm)
    # print("\n\n\n")
    
    # for ridx, rda in enumerate(c.rda):
    #     print("RDA", ridx)
    #     for sidx in range(len(rda)):
    #         print("Segment", sidx)
    #         print(rda(sidx))
    # print("\n\n\n")
    
    # print("Events")
    # print(c.events)
    # print("\n\n\n")

    # print("Category")
    # print(c.event_category)
    # print("\n\n\n")

    # cr = c.export_to_mne_raw(link_event=link_event, link_elt_plcm=1)

    
    # print("\n\n\nEDF annotation:", r.annotations)
    # print("Loaded annotation:", cr.annotations)

    # anns = [[f"{cr.annotations.onset[i]} ===> {cr.annotations.description[i]}"] for i in range(len(cr.annotations))]
    # max_len_c1 = 0
    # max_len_c2 = 0
    # for i in range(len(r.annotations)):
    #     anns[i].append(f"{r.annotations.onset[i]} ===> {r.annotations.description[i]}")
    #     anns[i].append(f"{cr.annotations.onset[i] - r.annotations.onset[i]}")
    #     if (l := len(anns[i][0])) > max_len_c1:
    #         max_len_c1 = l
    #     elif (l1 := len(anns[i][1])) > max_len_c2:
    #         max_len_c2 = l1

    # print("\n\n\nLoaded annotation" + " " * (max_len_c1 - 13) + "| EDF annotation" + " "* (max_len_c2 - 6) + "| Diff(sec)")
    # print("-" * (max_len_c1 + 4) + "+" + "-" * (max_len_c2 + 9) + "+" + "-" * 25)
    # for a in anns:
    #     print(a[0] + " " * (max_len_c1 - len(a[0]) + 4), end="")
    #     if len(a) > 1:
    #         print("|", a[1] + " " * (max_len_c2 - len(a[1]) + 8) + "|", a[2])
    #     else:
    #         print("| (None)" + " " * (max_len_c2 + 2) + "| (N/A)")
    
    # chs = ("Fp1", "Fp2", "F3", "F4", "F7", "F8", "T3", "T4", "T5", "T6", "C3", "C4", "P3", "P4", "O1", "O2", "Fz", "Pz", "Cz")

    # # cr = cr.pick(chs).set_eeg_reference("average")

    # cr = cr.filter(l_freq=0.5, h_freq=50)
    # r = r.filter(l_freq=0.5, h_freq=50)

    # cr.reorder_channels(chs).plot(start=1653.5, duration=1, scalings={"eeg": 60e-6})

    # # cr_ep = mne.Epochs(cr, tmin=-3, tmax=2)["Sharp Wave"]

    # # cr_ep.plot(n_epochs=5)

    # # cr_ev = cr_ep.average()

    # # cr_ev.plot()

    # r.pick(chs).plot(block=True, start=43.5, duration=1, scalings={"eeg": 60e-6})
    pass