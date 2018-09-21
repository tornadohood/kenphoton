"""Unit tests for hardware_utils."""

import gzip
import os
import unittest
import ujson

from photon.lib import custom_errors
from photon.lib import drive_utils
from photon.lib import hardware_utils
from photon.lib import test_utils

# pylint: disable=line-too-long
PATH = os.path.dirname(__file__)
FINDDRIVE_LINES = [
    '------------------------------------------------------------------------\n',
    '        Drive                  Nodes              Product          Rev                 SN     Expander    Enclosure            Slot\n',
    '     /dev/sg0                    sda  INTEL SSDSCKGW180A4         DC31   CVDA6176004J180H           NA       FA-x70         40186.4\n',
    '\n',
    '        Drive                  Nodes              Product          Rev                 SN     Expander    Enclosure            Slot  Subslot      SAT                  SAT_Rev\n',
    ' /dev/nvme7n1                nvme7n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN17436939            -     M_SERIES     10070-CH0.0        -        -                        -\n',
    '/dev/nvme15n1               nvme15n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN174369A1            -     M_SERIES     10070-CH0.1        -        -                        -\n',
    '/dev/nvme16n1               nvme16n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN174369D6            -     M_SERIES     10070-CH0.2        -        -                        -\n',
    '/dev/nvme14n1               nvme14n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN1743699F            -     M_SERIES     10070-CH0.3        -        -                        -\n',
    '/dev/nvme18n1               nvme18n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN174368F5            -     M_SERIES     10070-CH0.4        -        -                        -\n',
    '/dev/nvme13n1               nvme13n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN17436975            -     M_SERIES     10070-CH0.5        -        -                        -\n',
    '/dev/nvme19n1               nvme19n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN1743699E            -     M_SERIES     10070-CH0.6        -        -                        -\n',
    '/dev/nvme17n1               nvme17n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN17436969            -     M_SERIES     10070-CH0.7        -        -                        -\n',
    '/dev/nvme23n1               nvme23n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN17436936            -     M_SERIES     10070-CH0.8        -        -                        -\n',
    '/dev/nvme21n1               nvme21n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN17436937            -     M_SERIES     10070-CH0.9        -        -                        -\n',
    ' /dev/nvme0n1                nvme0n1       PURE NVRAM0101       0.3.10      PNVFS15420184            -     M_SERIES  10070-CH0.NVB0        -        -                        -\n',
    ' /dev/nvme1n1                nvme1n1       PURE NVRAM0101       0.3.10      PNVFS154300F0            -     M_SERIES  10070-CH0.NVB1        -        -                        -\n',
    ' /dev/nvme2n1                nvme2n1       PURE NVRAM0101       0.3.10      PNVFS15420181            -     M_SERIES  10070-CH0.NVB2        -        -                        -\n',
    ' /dev/nvme3n1                nvme3n1       PURE NVRAM0101       0.3.10      PNVFS154100AE            -     M_SERIES  10070-CH0.NVB3        -        -                        -\n',
    '\n',
    '        Drive                  Nodes              Product          Rev                 SN     Expander    Enclosure            Slot  Subslot      SAT                  SAT_Rev\n',
    '     /dev/sg1               sdb sdgk TOSHIBA THNSNJ512GCSU     JUPS0102       45JS11DMTGTW    /dev/sg25     EB-2425P       G4KFD-0.0        -      LSI   LSISS25x00011_00_02_00\n',
    '     /dev/sg2               sdgj sdc TOSHIBA THNSNH512GCST     HTPSN101       X4RS105BTVQY    /dev/sg25     EB-2425P       G4KFD-0.1        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg243              sdkd sdke TOSHIBA THNSNH512GCST     HTPSN101       X4RS107ATVQY    /dev/sg25     EB-2425P       G4KFD-0.2        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg242               sdgh sdk TOSHIBA THNSNH512GCST     HTPSN101       X4RS118KTVQY    /dev/sg25     EB-2425P       G4KFD-0.3        -      LSI   LSISS25x00011_00_02_00\n',
    '     /dev/sg9               sdgg sdj TOSHIBA THNSNH512GCST     HTPSN101       X4RS1076TVQY    /dev/sg25     EB-2425P       G4KFD-0.4        -      LSI   LSISS25x00011_00_02_00\n',
    '     /dev/sg8               sdgf sdi TOSHIBA THNSNH512GCST     HTPSN101       X4RS118ATVQY    /dev/sg25     EB-2425P       G4KFD-0.5        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg239               sdge sdh TOSHIBA THNSNH512GCST     HTPSN101       X4RS105GTVQY    /dev/sg25     EB-2425P       G4KFD-0.6        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg238               sdgd sdf TOSHIBA THNSNH512GCST     HTPSN101       X4RS1075TVQY    /dev/sg25     EB-2425P       G4KFD-0.7        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg237               sde sdgc TOSHIBA THNSNH512GCST     HTPSN101       X4RS118FTVQY    /dev/sg25     EB-2425P       G4KFD-0.8        -      LSI   LSISS25x00011_00_02_00\n',
    '     /dev/sg3               sdd sdgb TOSHIBA THNSNH512GCST     HTPSN101       X4RS1185TVQY    /dev/sg25     EB-2425P       G4KFD-0.9        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg235               sdg sdga TOSHIBA THNSNH512GCST     HTPSN101       X4RS107OTVQY    /dev/sg25     EB-2425P      G4KFD-0.10        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg234               sdl sdfz TOSHIBA THNSNH512GCST     HTPSN101       X4RS108NTVQY    /dev/sg25     EB-2425P      G4KFD-0.11        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg17               sdr sdfy TOSHIBA THNSNH512GCST     HTPSN101       X4RS107JTVQY    /dev/sg25     EB-2425P      G4KFD-0.12        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg16               sdq sdfx TOSHIBA THNSNH512GCST     HTPSN101       X4RS1056TVQY    /dev/sg25     EB-2425P      G4KFD-0.13        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg15               sdfw sdp TOSHIBA THNSNH512GCST     HTPSN101       X4RS107ETVQY    /dev/sg25     EB-2425P      G4KFD-0.14        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg230               sdfv sds TOSHIBA THNSNH512GCST     HTPSN101       X4RS118BTVQY    /dev/sg25     EB-2425P      G4KFD-0.15        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg229               sdfu sdv TOSHIBA THNSNH512GCST     HTPSN101       X4RS10TCTVQY    /dev/sg25     EB-2425P      G4KFD-0.16        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg228               sdu sdft TOSHIBA THNSNH512GCST     HTPSN101       X4RS10SWTVQY    /dev/sg25     EB-2425P      G4KFD-0.17        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg19               sdt sdfs TOSHIBA THNSNH512GCST     HTPSN101       X4RS10TBTVQY    /dev/sg25     EB-2425P      G4KFD-0.18        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg14               sdo sdfr TOSHIBA THNSNH512GCST     HTPSN101       X4RS10T1TVQY    /dev/sg25     EB-2425P      G4KFD-0.19        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg13               sdn sdfq TOSHIBA THNSNH512GCST     HTPSN101       X4RS10S8TVQY    /dev/sg25     EB-2425P      G4KFD-0.20        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg22               sdw sdfp TOSHIBA THNSNH512GCST     HTPSN101       X4RS10T6TVQY    /dev/sg25     EB-2425P      G4KFD-0.21        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg223               sdfo sdx TOSHIBA THNSNH512GCST     HTPSN101       X4RS10S2TVQY    /dev/sg25     EB-2425P      G4KFD-0.22        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg24               sdfn sdy TOSHIBA THNSNJ512GCSU     JUPS0102       45JS10D7TGTW    /dev/sg25     EB-2425P      G4KFD-0.23        -      LSI   LSISS25x00011_00_02_00\n',
    '\n',
    '        Drive                  Nodes              Product          Rev                 SN     Expander    Enclosure            Slot  Subslot      SAT                  SAT_Rev\n',
    '   /dev/sg197              sdaw sdep TOSHIBA THNSNJ512GCSU     JUPS0102       45JS11AVTGTW    /dev/sg50     EB-2425P       G4KGF-1.0        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg198              sdav sdeq TOSHIBA THNSNH512GCST     HTPSN101       X4RS1126TVQY    /dev/sg50     EB-2425P       G4KGF-1.1        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg47              sdau sdfa TOSHIBA THNSNH512GCST     HTPSN101       X4RS1139TVQY    /dev/sg50     EB-2425P       G4KGF-1.2        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg46              sdat sdey TOSHIBA THNSNH512GCST     HTPSN101       X4RS113PTVQY    /dev/sg50     EB-2425P       G4KGF-1.3        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg205              sdex sdas TOSHIBA THNSNH512GCST     HTPSN101       X4RS113ETVQY    /dev/sg50     EB-2425P       G4KGF-1.4        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg204              sdar sdew TOSHIBA THNSNH512GCST     HTPSN101       X4RS1134TVQY    /dev/sg50     EB-2425P       G4KGF-1.5        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg43              sdev sdaq TOSHIBA THNSNH512GCST     HTPSN101       X4RS10CATVQY    /dev/sg50     EB-2425P       G4KGF-1.6        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg201              sdap sdet TOSHIBA THNSNH512GCST     HTPSN101       X4RS1035TVQY    /dev/sg50     EB-2425P       G4KGF-1.7        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg200              sdes sdao TOSHIBA THNSNH512GCST     HTPSN101       X4RS103TTVQY    /dev/sg50     EB-2425P       G4KGF-1.8        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg199              sder sdan TOSHIBA THNSNH512GCST     HTPSN101       X4RS10D4TVQY    /dev/sg50     EB-2425P       G4KGF-1.9        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg39              sdam sdeu TOSHIBA THNSNH512GCST     HTPSN101       X4RS10C7TVQY    /dev/sg50     EB-2425P      G4KGF-1.10        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg207              sdez sdal TOSHIBA THNSNH512GCST     HTPSN101       X4RS10CCTVQY    /dev/sg50     EB-2425P      G4KGF-1.11        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg37              sdff sdak TOSHIBA THNSNH512GCST     HTPSN101       X4RS10BLTVQY    /dev/sg50     EB-2425P      G4KGF-1.12        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg36              sdfe sdaj TOSHIBA THNSNH512GCST     HTPSN101       X4RS10BZTVQY    /dev/sg50     EB-2425P      G4KGF-1.13        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg35              sdfd sdai TOSHIBA THNSNH512GCST     HTPSN101       X4RS10CITVQY    /dev/sg50     EB-2425P      G4KGF-1.14        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg214              sdfg sdah TOSHIBA THNSNH512GCST     HTPSN101       X4RS10CKTVQY    /dev/sg50     EB-2425P      G4KGF-1.15        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg217              sdag sdfj TOSHIBA THNSNH512GCST     HTPSN101       X4RS10BCTVQY    /dev/sg50     EB-2425P      G4KGF-1.16        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg216              sdaf sdfi TOSHIBA THNSNH512GCST     HTPSN101       X4RS10D0TVQY    /dev/sg50     EB-2425P      G4KGF-1.17        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg215              sdae sdfh TOSHIBA THNSNH512GCST     HTPSN101       X4RS10C6TVQY    /dev/sg50     EB-2425P      G4KGF-1.18        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg210              sdad sdfc TOSHIBA THNSNH512GCST     HTPSN101       X4RS10CRTVQY    /dev/sg50     EB-2425P      G4KGF-1.19        -      LSI   LSISS25x00011_00_02_00\n',
    '   /dev/sg209              sdfb sdac TOSHIBA THNSNH512GCST     HTPSN101       X4RS10BETVQY    /dev/sg50     EB-2425P      G4KGF-1.20        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg28              sdab sdfk TOSHIBA THNSNH512GCST     HTPSN101       X4RS10B4TVQY    /dev/sg50     EB-2425P      G4KGF-1.21        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg27              sdfl sdaa TOSHIBA THNSNH512GCST     HTPSN101       X4QS10QUTVQY    /dev/sg50     EB-2425P      G4KGF-1.22        -      LSI   LSISS25x00011_00_02_00\n',
    '    /dev/sg26               sdfm sdz TOSHIBA THNSNJ512GCSU     JUPS0102       45JS112OTGTW    /dev/sg50     EB-2425P      G4KGF-1.23        -      LSI   LSISS25x00011_00_02_00\n',
    '\n',
    '        Drive                  Nodes              Product          Rev                 SN     Expander    Enclosure            Slot  Subslot      SAT                  SAT_Rev\n',
    '   /dev/sg272              sdhb sddh SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600488   /dev/sg319     EB-2425-       RCCAT-2.0        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg273              sdhc sddi SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600487   /dev/sg319     EB-2425-       RCCAT-2.0        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg143              sddf sdhd SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600535   /dev/sg319     EB-2425-       RCCAT-2.1        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg144              sddg sdhe SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600540   /dev/sg319     EB-2425-       RCCAT-2.1        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg278              sdeh sdhf SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600539   /dev/sg319     EB-2425-       RCCAT-2.2        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg186              sdei sdhg SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600533   /dev/sg319     EB-2425-       RCCAT-2.2        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg191              sdhh sdel SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600530   /dev/sg319     EB-2425-       RCCAT-2.3        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg192              sdhi sdem SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600524   /dev/sg319     EB-2425-       RCCAT-2.3        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg284              sdhj sden SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600526   /dev/sg319     EB-2425-       RCCAT-2.4        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg285              sdhk sdeo SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600527   /dev/sg319     EB-2425-       RCCAT-2.4        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg125              sdct sdhl SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600541   /dev/sg319     EB-2425-       RCCAT-2.5        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg126              sdhm sdcu SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600536   /dev/sg319     EB-2425-       RCCAT-2.5        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg128              sdcv sdhn SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600522   /dev/sg319     EB-2425-       RCCAT-2.6        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg129              sdho sdcw SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600516   /dev/sg319     EB-2425-       RCCAT-2.6        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg293              sdhp sdcz SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600545   /dev/sg319     EB-2425-       RCCAT-2.7        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg294              sdhq sdda SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600543   /dev/sg319     EB-2425-       RCCAT-2.7        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg296              sdhr sddb SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600497   /dev/sg319     EB-2425-       RCCAT-2.8        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg297              sdhs sddc SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600486   /dev/sg319     EB-2425-       RCCAT-2.8        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg140              sddd sdht SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600538   /dev/sg319     EB-2425-       RCCAT-2.9        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg141              sdde sdhu SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600529   /dev/sg319     EB-2425-       RCCAT-2.9        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg131              sdcx sdhv SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600525   /dev/sg319     EB-2425-      RCCAT-2.10        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg132              sdcy sdhw SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600518   /dev/sg319     EB-2425-      RCCAT-2.10        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg305              sdej sdhx SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600496   /dev/sg319     EB-2425-      RCCAT-2.11        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg306              sdhy sdek SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNX0H600491   /dev/sg319     EB-2425-      RCCAT-2.11        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg308              sdhz sddx SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH306216   /dev/sg319     EB-2425-      RCCAT-2.12        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg309              sddy sdia SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH306219   /dev/sg319     EB-2425-      RCCAT-2.12        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg311              sdib sddz SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH304789   /dev/sg319     EB-2425-      RCCAT-2.13        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg312              sdea sdic SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH304787   /dev/sg319     EB-2425-      RCCAT-2.13        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg176              sdeb sdid SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH306218   /dev/sg319     EB-2425-      RCCAT-2.14        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg177              sdec sdie SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH306229   /dev/sg319     EB-2425-      RCCAT-2.14        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg317              sdif sddv SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH306182   /dev/sg319     EB-2425-      RCCAT-2.15        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg168              sdig sddw SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH306172   /dev/sg319     EB-2425-      RCCAT-2.15        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg158              sdgl sddp SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH304949   /dev/sg319     EB-2425-      RCCAT-2.16        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg159              sdgm sddq SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH304942   /dev/sg319     EB-2425-      RCCAT-2.16        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg161              sdgn sddr SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH306175   /dev/sg319     EB-2425-      RCCAT-2.17        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg252              sdgo sdds SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH306207   /dev/sg319     EB-2425-      RCCAT-2.17        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg164              sddt sdgp SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH306200   /dev/sg319     EB-2425-      RCCAT-2.18        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg165              sddu sdgq SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH306206   /dev/sg319     EB-2425-      RCCAT-2.18        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg257              sdgr sded SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH306296   /dev/sg319     EB-2425-      RCCAT-2.19        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg258              sdgs sdee SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH306282   /dev/sg319     EB-2425-      RCCAT-2.19        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg182              sdgt sdef SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH304946   /dev/sg319     EB-2425-      RCCAT-2.20        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg183              sdgu sdeg SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH304932   /dev/sg319     EB-2425-      RCCAT-2.20        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg155              sdgv sddn SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH304935   /dev/sg319     EB-2425-      RCCAT-2.21        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg264              sddo sdgw SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH304937   /dev/sg319     EB-2425-      RCCAT-2.21        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg266              sddl sdgx SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH304938   /dev/sg319     EB-2425-      RCCAT-2.22        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg267              sddm sdgy SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH304939   /dev/sg319     EB-2425-      RCCAT-2.22        2  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg149              sdgz sddj SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH304783   /dev/sg319     EB-2425-      RCCAT-2.23        1  MARVELL       0M1S3096020000ST00\n',
    '   /dev/sg270              sdha sddk SAMSUNG MZ7LM960HCHP-00003     GXT33P3Q     S1YHNXAH304797   /dev/sg319     EB-2425-      RCCAT-2.23        2  MARVELL       0M1S3096020000ST00\n',
    '\n',
    '        Drive                  Nodes              Product          Rev                 SN     Expander    Enclosure            Slot  Subslot      SAT                  SAT_Rev\n',
    '   /dev/sg342              sdiv sdbn TOSHIBA THNSNJ1T02CSX     JXPS4101       Z5HS1102TGUW   /dev/sg392     EB-2425-       G1Y1L-3.0        1  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg343              sdiw sdbo TOSHIBA THNSNJ1T02CSX     JXPS4101       Z5HS10ZATGUW   /dev/sg392     EB-2425-       G1Y1L-3.0        2  MARVELL       0M1T2102420000ST00\n',
    '    /dev/sg79              sdit sdbp TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10WWTGUW   /dev/sg392     EB-2425-       G1Y1L-3.1        1  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg340              sdbq sdiu TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10WNTGUW   /dev/sg392     EB-2425-       G1Y1L-3.1        2  MARVELL       0M1T2102420000ST00\n',
    '    /dev/sg82              sdbr sdjv TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10WSTGUW   /dev/sg392     EB-2425-       G1Y1L-3.2        1  MARVELL       0M1T2102420000ST00\n',
    '    /dev/sg83              sdbs sdjw TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10XBTGUW   /dev/sg392     EB-2425-       G1Y1L-3.2        2  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg387              sdjz sdbt TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10MLTGUW   /dev/sg392     EB-2425-       G1Y1L-3.3        1  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg388              sdka sdbu TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10NUTGUW   /dev/sg392     EB-2425-       G1Y1L-3.3        2  MARVELL       0M1T2102420000ST00\n',
    '    /dev/sg88              sdkb sdbv TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10SPTGUW   /dev/sg392     EB-2425-       G1Y1L-3.4        1  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg391              sdkc sdbw TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10XKTGUW   /dev/sg392     EB-2425-       G1Y1L-3.4        2  MARVELL       0M1T2102420000ST00\n',
    '    /dev/sg91              sdbx sdih TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S11MOTGUW   /dev/sg392     EB-2425-       G1Y1L-3.5        1  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg322              sdby sdii TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S11MFTGUW   /dev/sg392     EB-2425-       G1Y1L-3.5        2  MARVELL       0M1T2102420000ST00\n',
    '    /dev/sg94              sdbz sdij TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10SFTGUW   /dev/sg392     EB-2425-       G1Y1L-3.6        1  MARVELL       0M1T2102420000ST00\n',
    '    /dev/sg95              sdca sdik TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10S5TGUW   /dev/sg392     EB-2425-       G1Y1L-3.6        2  MARVELL       0M1T2102420000ST00\n',
    '    /dev/sg97              sdin sdcb TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10WRTGUW   /dev/sg392     EB-2425-       G1Y1L-3.7        1  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg331              sdio sdcc TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10XJTGUW   /dev/sg392     EB-2425-       G1Y1L-3.7        2  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg100              sdcd sdip TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS104NTGUW   /dev/sg392     EB-2425-       G1Y1L-3.8        1  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg334              sdce sdiq TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS102UTGUW   /dev/sg392     EB-2425-       G1Y1L-3.8        2  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg336              sdir sdcf TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS103VTGUW   /dev/sg392     EB-2425-       G1Y1L-3.9        1  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg337              sdis sdcg TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS107BTGUW   /dev/sg392     EB-2425-       G1Y1L-3.9        2  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg106              sdch sdil TOSHIBA THNSNJ1T02CSY     JYPS4101       37QS10DBTV5V   /dev/sg392     EB-2425-      G1Y1L-3.10        1  MARVELL       0M1T3102420000ST00\n',
    '   /dev/sg107              sdci sdim TOSHIBA THNSNJ1T02CSY     JYPS4101       37QS10BVTV5V   /dev/sg392     EB-2425-      G1Y1L-3.10        2  MARVELL       0M1T3102420000ST00\n',
    '   /dev/sg384              sdcj sdjx TOSHIBA THNSNJ1T02CSY     JYPS4101       47MS1027TV5V   /dev/sg392     EB-2425-      G1Y1L-3.11        1  MARVELL       0M1T3102420000ST00\n',
    '   /dev/sg385              sdjy sdck TOSHIBA THNSNJ1T02CSY     JYPS4101       47MS100NTV5V   /dev/sg392     EB-2425-      G1Y1L-3.11        2  MARVELL       0M1T3102420000ST00\n',
    '   /dev/sg366              sdcl sdjl TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS103CTGUW   /dev/sg392     EB-2425-      G1Y1L-3.12        1  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg367              sdcm sdjm TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS1033TGUW   /dev/sg392     EB-2425-      G1Y1L-3.12        2  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg115              sdjn sdcn TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS1038TGUW   /dev/sg392     EB-2425-      G1Y1L-3.13        1  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg370              sdjo sdco TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS103HTGUW   /dev/sg392     EB-2425-      G1Y1L-3.13        2  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg372              sdcp sdjp TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS1035TGUW   /dev/sg392     EB-2425-      G1Y1L-3.14        1  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg373              sdcq sdjq TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS108HTGUW   /dev/sg392     EB-2425-      G1Y1L-3.14        2  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg363              sdjj sdcr TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS1032TGUW   /dev/sg392     EB-2425-      G1Y1L-3.15        1  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg364              sdjk sdcs TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS102PTGUW   /dev/sg392     EB-2425-      G1Y1L-3.15        2  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg354              sdax sdjd TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS102YTGUW   /dev/sg392     EB-2425-      G1Y1L-3.16        1  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg355              sdje sday TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS102TTGUW   /dev/sg392     EB-2425-      G1Y1L-3.16        2  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg357              sdaz sdjf TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS102XTGUW   /dev/sg392     EB-2425-      G1Y1L-3.17        1  MARVELL       0M1T2102420000ST00\n',
    '    /dev/sg56              sdba sdjg TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS1037TGUW   /dev/sg392     EB-2425-      G1Y1L-3.17        2  MARVELL       0M1T2102420000ST00\n',
    '    /dev/sg58              sdbb sdjh TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS103NTGUW   /dev/sg392     EB-2425-      G1Y1L-3.18        1  MARVELL       0M1T2102420000ST00\n',
    '    /dev/sg59              sdbc sdji TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS102STGUW   /dev/sg392     EB-2425-      G1Y1L-3.18        2  MARVELL       0M1T2102420000ST00\n',
    '    /dev/sg61              sdjr sdbd TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS10BUTGUW   /dev/sg392     EB-2425-      G1Y1L-3.19        1  MARVELL       0M1T2102420000ST00\n',
    '    /dev/sg62              sdjs sdbe TOSHIBA THNSNJ1T02CSX     JXPS4101       X5LS10C4TGUW   /dev/sg392     EB-2425-      G1Y1L-3.19        2  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg378              sdbf sdjt TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10XLTGUW   /dev/sg392     EB-2425-      G1Y1L-3.20        1  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg379              sdbg sdju TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10WETGUW   /dev/sg392     EB-2425-      G1Y1L-3.20        2  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg351              sdjb sdbh TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10X1TGUW   /dev/sg392     EB-2425-      G1Y1L-3.21        1  MARVELL       0M1T2102420000ST00\n',
    '    /dev/sg68              sdjc sdbi TOSHIBA THNSNJ1T02CSX     JXPS4101       Y55S10WDTGUW   /dev/sg392     EB-2425-      G1Y1L-3.21        2  MARVELL       0M1T2102420000ST00\n',
    '   /dev/sg348              sdbj sdiz TOSHIBA THNSNJ1T02CSY     JYPS4101       37QS10SKTV5V   /dev/sg392     EB-2425-      G1Y1L-3.22        1  MARVELL       0M1T3102420000ST00\n',
    '   /dev/sg349              sdbk sdja TOSHIBA THNSNJ1T02CSY     JYPS4101       37QS10SATV5V   /dev/sg392     EB-2425-      G1Y1L-3.22        2  MARVELL       0M1T3102420000ST00\n',
    '    /dev/sg73              sdix sdbl TOSHIBA THNSNJ1T02CSY     JYPS4101       471S1031TV5V   /dev/sg392     EB-2425-      G1Y1L-3.23        1  MARVELL       0M1T3102420000ST00\n',
    '   /dev/sg346              sdbm sdiy TOSHIBA THNSNJ1T02CSY     JYPS4101       471S102MTV5V   /dev/sg392     EB-2425-      G1Y1L-3.23        2  MARVELL       0M1T3102420000ST00\n',
    '\n',
    '\n'
]
PUREHW_LINES = [
    '------------------------------------------------------------------------\n',
    'Name       Status         Identify  Slot  Index  Speed       Temperature  Voltage  Type           Handle                                   Parent                              \n',
    'CH0        ok             off       -     0      -           -            -        chassis        TUNGPCIB_PCHFS15410070                   hwroot                              \n',
    'CH0.BAY0   ok             off       -     0      -           -            -        drive_bay      TUNGPCIB_PCHFS15410070_nvme_wssd_bay0    TUNGPCIB_PCHFS15410070              \n',
    'CH0.BAY10  not_installed  off       -     10     -           -            -        drive_bay      TUNGPCIB_PCHFS15410070_nvme_wssd_bay10   TUNGPCIB_PCHFS15410070              \n',
    'CH0.NVB0   ok             off       -     0      -           -            -        nvram_bay      TUNGPCIB_PCHFS15410070_nvme_nvram_bay0   TUNGPCIB_PCHFS15410070              \n',
    'CH0.PWR0   ok             -         -     0      -           -            204 V    power_supply   TUNGPCIB_PCHFS15410070_psu0              TUNGPCIB_PCHFS15410070              \n',
    'CT0        ok             off       -     0      -           -            -        controller     TUNGPCIB_PCTFL17420014                   TUNGPCIB_PCHFS15410070              \n',
    'CT0.ETH0   ok             -         -     0      1.00 Gb/s   -            -        eth_port       TUNGPCIB_PCTFL17420014_0000:18:00.0_p0   TUNGPCIB_PCTFL17420014              \n',
    'CT0.FAN0   ok             -         -     0      -           -            -        cooling        TUNGPCIB_PCTFL17420014_sens96            TUNGPCIB_PCTFL17420014              \n',
    'CT0.FC0    ok             -         2     0      8.00 Gb/s   -            -        fc_port        TUNGPCIB_PCTFL17420014_0000:82:00.0_p0   TUNGPCIB_PCTFL17420014              \n',
    'CT0.SAS0   ok             -         -     0      24.00 Gb/s  -            -        sas_port       TUNGPCIB_PCTFL17420014_0000:04:00.0_p0   TUNGPCIB_PCTFL17420014              \n',
    'CT0.TMP0   ok             -         -     0      -           49 C         -        temp_sensor    TUNGPCIB_PCTFL17420014_sens64            TUNGPCIB_PCTFL17420014              \n',
    'CT1        ok             off       -     1      -           -            -        controller     TUNGPCIB_PCTFL17340186                   TUNGPCIB_PCHFS15410070              \n',
    'CT1.ETH0   ok             -         -     0      1.00 Gb/s   -            -        eth_port       TUNGPCIB_PCTFL17340186_0000:18:00.0_p0   TUNGPCIB_PCTFL17340186              \n',
    'CT1.FAN0   ok             -         -     0      -           -            -        cooling        TUNGPCIB_PCTFL17340186_sens96            TUNGPCIB_PCTFL17340186              \n',
    'CT1.FC0    ok             -         2     0      8.00 Gb/s   -            -        fc_port        TUNGPCIB_PCTFL17340186_0000:82:00.0_p0   TUNGPCIB_PCTFL17340186              \n',
    'CT1.SAS0   ok             -         -     0      24.00 Gb/s  -            -        sas_port       TUNGPCIB_PCTFL17340186_0000:04:00.0_p0   TUNGPCIB_PCTFL17340186              \n',
    'CT1.TMP0   ok             -         -     0      -           38 C         -        temp_sensor    TUNGPCIB_PCTFL17340186_sens64            TUNGPCIB_PCTFL17340186              \n',
    'SH0        ok             off       -     0      -           -            -        storage_shelf  EB-2425P-E6EBD_SHG0998507G4KFD           hwroot                              \n',
    'SH0.BAY0   ok             off       -     0      -           -            -        drive_bay      EB-2425P-E6EBD_SHG0998507G4KFD_ses1      EB-2425P-E6EBD_SHG0998507G4KFD      \n',
    'SH0.FAN0   ok             -         -     0      -           -            -        cooling        EB-2425P-E6EBD_SHG0998507G4KFD_ses29     EB-2425P-E6EBD_SHG0998507G4KFD_ses26\n',
    'SH0.IOM0   ok             off       0     0      -           -            -        sas_module     EB-2425P-E6EBD_SHG0998507G4KFD_ses46     EB-2425P-E6EBD_SHG0998507G4KFD      \n',
    'SH0.PWR0   ok             -         -     0      -           -            -        power_supply   EB-2425P-E6EBD_SHG0998507G4KFD_ses26     EB-2425P-E6EBD_SHG0998507G4KFD      \n',
    'SH0.SAS0   ok             -         0     0      24.00 Gb/s  -            -        sas_port       EB-2425P-E6EBD_SHG0998507G4KFD_ses46_p0  EB-2425P-E6EBD_SHG0998507G4KFD      \n',
    'SH0.TMP0   ok             -         -     0      -           10 C         -        temp_sensor    EB-2425P-E6EBD_SHG0998507G4KFD_ses34     EB-2425P-E6EBD_SHG0998507G4KFD      \n',
    '\n']
HW_CHECK_LINES = [
    '',
    'Apr 12 00:17:54 hardware_check.py',
    '------------------------------------------------------------------------',
    '',
    '==== CPU ====',
    'model name      : Intel(R) Xeon(R) CPU E5-2698 v4 @ 2.20GHz        x 80',
    '',
    '==== RAM ====',
    'MemTotal:       1056547520 kB',
    '',
    '==== FC TARGETS ====',
    'Detected 6 targets.',
    'Found 6 FC adapter ports.',
    '',
    '==== iSCSI TARGETS ====',
    'Detected 2 iSCSI capable ports',
    '',
    '==== NON-TRANSPARENT BRIDGE ====',
    'Found NTB: 80:03.0 Bridge [0680]: Intel Corporation Device [8086:6f0d] (rev 01)',
    'Bar 2 Size: 256G',
    '',
    '==== INFINIBAND ADAPTERS ====',
    'No IB adapters found.',
    '',
    '==== STORAGE ====',
    'summary: enclosures: 5, drives: 141, drive models: 4',
    "enclosure: G4XJ4-0, drives {'TOSHIBA THNSNJ1T02CSX': 24}, revs {'JXPS4101': 24}, paths 48",
    "enclosure: 1023A, drives {'INTEL SSDSCKGW180A4': 1}, revs {'DC31': 1}, paths 1",
    "enclosure: 30028-CH0, drives {'TOSHIBA THNSNJ1T02CSX': 40, 'PURE NVRAM0101': 4}, revs {'JXPS4101': 40, '0.3.10': 4}, paths 44",
    "enclosure: G4XHL-1, drives {'TOSHIBA THNSNJ1T02CSX': 24}, revs {'JXPS4101': 24}, paths 48",
    "enclosure: G0YYC-2, drives {'SAMSUNG MZ7LM1T9HMJP-00005': 48}, revs {'GXT51P4Q': 48}, paths 96",
    'SAS Expanders found: 6',
    '',
    '==== Results ====',
    "All's well.",
    '',
]


class DummyStorageGroup(hardware_utils.StorageGroup):
    """Test helper for StorageGroup."""

    @property
    def compatible_components(self):
        """This is compatible with SSDs-only for testing."""
        return drive_utils.SSD


class GetParentNameTestCase(unittest.TestCase):
    """Unit tests for get_parent_name."""
    with gzip.open(test_utils.get_files_of_type('Uncategorized/purehw_list.json')[0]) as json_file:
        purehw_info = ujson.load(json_file, precise_float=True)
    parsed_hw_info = hardware_utils.parse_purehw_list(sorted(purehw_info['CT0']['purehw_list'])[-1][1])

    def test_parent_not_present(self):
        """Test failing to find the parent by its handle."""
        with self.assertRaises(custom_errors.InsufficientDataError):
            hardware_utils.get_parent_name('fake_handle', self.parsed_hw_info)

    def test_shelf_parent(self):
        """Test fetching a specific shelf by its handle."""
        # EB-2425P-E6EBD_SHG0998507G4KFD -> SH0
        expected = 'SH0'
        result = hardware_utils.get_parent_name('EB-2425P-E6EBD_SHG0998507G4KFD', self.parsed_hw_info)
        self.assertEqual(expected, result)


class HBATestCase(unittest.TestCase):
    """Unit tests for HBA."""
    hba = hardware_utils.HBA('Test HBA')

    def test_add_component(self):
        """Test adding a port to the HBA."""
        port1 = hardware_utils.Port('Port 1')
        self.hba.add_component(port1)
        self.assertEqual(list(self.hba.components.keys()), ['Port 1'])

    def test_bad_component(self):
        """Test adding an unsupported component."""
        ipmi = hardware_utils.IPMI('Test IPMI')
        with self.assertRaises(custom_errors.HardwareCompatibilityError):
            self.hba.add_component(ipmi)


class HWComponentTestCase(unittest.TestCase):
    """Unit tests for HWComponent."""

    def test_build(self):
        """Test instantiating a Hardware Component."""
        test_component = hardware_utils.HardwareComponent('My Component', 'Component Type')
        self.assertTrue(test_component)

    def test_conflicting_kwargs(self):
        """Test instantiating with namespace conflicts from kwargs."""
        kwargs = {'name': 'this name should conflict with the name attribute.'}
        with self.assertRaises(TypeError):
            # This is intentional for testing purposes.
            # pylint: disable=redundant-keyword-arg
            hardware_utils.HardwareComponent('Test Component', 'Component Type', **kwargs)


class HardwareGroupTestCase(unittest.TestCase):
    """Unit tests for HardwareGroup."""
    test_group = hardware_utils.HardwareGroup('My Group')

    def test_build(self):
        """Test instantiating a HardwareGroup."""
        self.assertTrue(self.test_group)


class IOMTestCase(unittest.TestCase):
    """Unit tests for IOM."""
    iom = hardware_utils.IOM('Test IOM')

    def test_add_component(self):
        """Test adding a port to the IOM."""
        port1 = hardware_utils.Port('Port 1')
        self.iom.add_component(port1)
        self.assertEqual(list(self.iom.components.keys()), ['Port 1'])

    def test_bad_component(self):
        """Test adding an unsupported component."""
        ipmi = hardware_utils.IPMI('Test IPMI')
        with self.assertRaises(custom_errors.HardwareCompatibilityError):
            self.iom.add_component(ipmi)


class IPMITestCase(unittest.TestCase):
    """Unit tests for IPMI."""
    ipmi = hardware_utils.IPMI('Test IPMI')

    def test_add_component(self):
        """Test adding a port to the IPMI."""
        sensor1 = hardware_utils.Sensor('Sensor 1')
        self.ipmi.add_component(sensor1)
        self.assertEqual(list(self.ipmi.components.keys()), ['Sensor 1'])

    def test_bad_component(self):
        """Test adding an unsupported component."""
        ipmi = hardware_utils.IPMI('Test IPMI')
        with self.assertRaises(custom_errors.HardwareCompatibilityError):
            self.ipmi.add_component(ipmi)


class NICTestCase(unittest.TestCase):
    """Unit tests for NIC."""
    nic = hardware_utils.NIC('Test NIC')

    def test_add_component(self):
        """Test adding a port to the NIC."""
        port1 = hardware_utils.Port('Port 1')
        self.nic.add_component(port1)
        self.assertEqual(list(self.nic.components.keys()), ['Port 1'])

    def test_bad_component(self):
        """Test adding an unsupported component."""
        ipmi = hardware_utils.IPMI('Test IPMI')
        with self.assertRaises(custom_errors.HardwareCompatibilityError):
            self.nic.add_component(ipmi)


class ParseHardwareCheckTestCase(unittest.TestCase):
    """Unit tests for parse_hardware_check."""

    def test_valid_lines(self):
        """Test with valid input lines."""
        expected = {}
        result = hardware_utils.parse_hardware_check(HW_CHECK_LINES)
        self.assertEqual(result, expected)


class ParsePureHWListTestCase(unittest.TestCase):
    """Unit tests for parse_purehw_list."""

    def test_valid_lines(self):
        """Test parsing valid purehw_list output lines."""
        expected = {'SH0': {'Speed': '-', 'Name': 'SH0', 'Parent': 'hwroot', 'Handle': 'EB-2425P-E6EBD_SHG0998507G4KFD',
                            'Voltage': '-', 'Status': 'ok', 'Type': 'storage_shelf', 'Identify': 'off',
                            'Temperature': '-', 'Index': '0', 'Slot': '-'},
                    'SH0.IOM0': {'Speed': '-', 'Name': 'SH0.IOM0', 'Parent': 'EB-2425P-E6EBD_SHG0998507G4KFD',
                                 'Handle': 'EB-2425P-E6EBD_SHG0998507G4KFD_ses46', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'sas_module', 'Identify': 'off', 'Temperature': '-', 'Index': '0',
                                 'Slot': '0'},
                    'SH0.PWR0': {'Speed': '-', 'Name': 'SH0.PWR0', 'Parent': 'EB-2425P-E6EBD_SHG0998507G4KFD',
                                 'Handle': 'EB-2425P-E6EBD_SHG0998507G4KFD_ses26', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'power_supply', 'Identify': '-', 'Temperature': '-', 'Index': '0',
                                 'Slot': '-'},
                    'CT0.FC0': {'Speed': '8.00 Gb/s', 'Name': 'CT0.FC0', 'Parent': 'TUNGPCIB_PCTFL17420014',
                                'Handle': 'TUNGPCIB_PCTFL17420014_0000:82:00.0_p0', 'Voltage': '-', 'Status': 'ok',
                                'Type': 'fc_port', 'Identify': '-', 'Temperature': '-', 'Index': '0', 'Slot': '2'},
                    'CH0.NVB0': {'Speed': '-', 'Name': 'CH0.NVB0', 'Parent': 'TUNGPCIB_PCHFS15410070',
                                 'Handle': 'TUNGPCIB_PCHFS15410070_nvme_nvram_bay0', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'nvram_bay', 'Identify': 'off', 'Temperature': '-', 'Index': '0',
                                 'Slot': '-'},
                    'CT0': {'Speed': '-', 'Name': 'CT0', 'Parent': 'TUNGPCIB_PCHFS15410070',
                            'Handle': 'TUNGPCIB_PCTFL17420014', 'Voltage': '-', 'Status': 'ok', 'Type': 'controller',
                            'Identify': 'off', 'Temperature': '-', 'Index': '0', 'Slot': '-'},
                    'CT1.SAS0': {'Speed': '24.00 Gb/s', 'Name': 'CT1.SAS0', 'Parent': 'TUNGPCIB_PCTFL17340186',
                                 'Handle': 'TUNGPCIB_PCTFL17340186_0000:04:00.0_p0', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'sas_port', 'Identify': '-', 'Temperature': '-', 'Index': '0', 'Slot': '-'},
                    'SH0.FAN0': {'Speed': '-', 'Name': 'SH0.FAN0', 'Parent': 'EB-2425P-E6EBD_SHG0998507G4KFD_ses26',
                                 'Handle': 'EB-2425P-E6EBD_SHG0998507G4KFD_ses29', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'cooling', 'Identify': '-', 'Temperature': '-', 'Index': '0', 'Slot': '-'},
                    'CT0.FAN0': {'Speed': '-', 'Name': 'CT0.FAN0', 'Parent': 'TUNGPCIB_PCTFL17420014',
                                 'Handle': 'TUNGPCIB_PCTFL17420014_sens96', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'cooling', 'Identify': '-', 'Temperature': '-', 'Index': '0', 'Slot': '-'},
                    'SH0.SAS0': {'Speed': '24.00 Gb/s', 'Name': 'SH0.SAS0', 'Parent': 'EB-2425P-E6EBD_SHG0998507G4KFD',
                                 'Handle': 'EB-2425P-E6EBD_SHG0998507G4KFD_ses46_p0', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'sas_port', 'Identify': '-', 'Temperature': '-', 'Index': '0', 'Slot': '0'},
                    'CT0.SAS0': {'Speed': '24.00 Gb/s', 'Name': 'CT0.SAS0', 'Parent': 'TUNGPCIB_PCTFL17420014',
                                 'Handle': 'TUNGPCIB_PCTFL17420014_0000:04:00.0_p0', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'sas_port', 'Identify': '-', 'Temperature': '-', 'Index': '0', 'Slot': '-'},
                    'CT0.TMP0': {'Speed': '-', 'Name': 'CT0.TMP0', 'Parent': 'TUNGPCIB_PCTFL17420014',
                                 'Handle': 'TUNGPCIB_PCTFL17420014_sens64', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'temp_sensor', 'Identify': '-', 'Temperature': '49 C', 'Index': '0',
                                 'Slot': '-'},
                    'CT1.TMP0': {'Speed': '-', 'Name': 'CT1.TMP0', 'Parent': 'TUNGPCIB_PCTFL17340186',
                                 'Handle': 'TUNGPCIB_PCTFL17340186_sens64', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'temp_sensor', 'Identify': '-', 'Temperature': '38 C', 'Index': '0',
                                 'Slot': '-'},
                    'CT1.ETH0': {'Speed': '1.00 Gb/s', 'Name': 'CT1.ETH0', 'Parent': 'TUNGPCIB_PCTFL17340186',
                                 'Handle': 'TUNGPCIB_PCTFL17340186_0000:18:00.0_p0', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'eth_port', 'Identify': '-', 'Temperature': '-', 'Index': '0', 'Slot': '-'},
                    'CH0.BAY0': {'Speed': '-', 'Name': 'CH0.BAY0', 'Parent': 'TUNGPCIB_PCHFS15410070',
                                 'Handle': 'TUNGPCIB_PCHFS15410070_nvme_wssd_bay0', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'drive_bay', 'Identify': 'off', 'Temperature': '-', 'Index': '0', 'Slot': '-'},
                    'CT0.ETH0': {'Speed': '1.00 Gb/s', 'Name': 'CT0.ETH0', 'Parent': 'TUNGPCIB_PCTFL17420014',
                                 'Handle': 'TUNGPCIB_PCTFL17420014_0000:18:00.0_p0', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'eth_port', 'Identify': '-', 'Temperature': '-', 'Index': '0', 'Slot': '-'},
                    'CT1.FC0': {'Speed': '8.00 Gb/s', 'Name': 'CT1.FC0', 'Parent': 'TUNGPCIB_PCTFL17340186',
                                'Handle': 'TUNGPCIB_PCTFL17340186_0000:82:00.0_p0', 'Voltage': '-', 'Status': 'ok',
                                'Type': 'fc_port', 'Identify': '-', 'Temperature': '-', 'Index': '0', 'Slot': '2'},
                    'CH0.BAY10': {'Speed': '-', 'Name': 'CH0.BAY10', 'Parent': 'TUNGPCIB_PCHFS15410070',
                                  'Handle': 'TUNGPCIB_PCHFS15410070_nvme_wssd_bay10', 'Voltage': '-', 'Status':
                                      'not_installed', 'Type': 'drive_bay', 'Identify': 'off', 'Temperature': '-',
                                  'Index': '10', 'Slot': '-'},
                    'CT1.FAN0': {'Speed': '-', 'Name': 'CT1.FAN0', 'Parent': 'TUNGPCIB_PCTFL17340186',
                                 'Handle': 'TUNGPCIB_PCTFL17340186_sens96', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'cooling', 'Identify': '-', 'Temperature': '-', 'Index': '0', 'Slot': '-'},
                    'SH0.TMP0': {'Speed': '-', 'Name': 'SH0.TMP0', 'Parent': 'EB-2425P-E6EBD_SHG0998507G4KFD',
                                 'Handle': 'EB-2425P-E6EBD_SHG0998507G4KFD_ses34', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'temp_sensor', 'Identify': '-', 'Temperature': '10 C', 'Index': '0',
                                 'Slot': '-'},
                    'CH0.PWR0': {'Speed': '-', 'Name': 'CH0.PWR0', 'Parent': 'TUNGPCIB_PCHFS15410070',
                                 'Handle': 'TUNGPCIB_PCHFS15410070_psu0', 'Voltage': '204 V', 'Status': 'ok',
                                 'Type': 'power_supply', 'Identify': '-', 'Temperature': '-', 'Index': '0',
                                 'Slot': '-'},
                    'CH0': {'Speed': '-', 'Name': 'CH0', 'Parent': 'hwroot', 'Handle': 'TUNGPCIB_PCHFS15410070',
                            'Voltage': '-', 'Status': 'ok', 'Type': 'chassis', 'Identify': 'off', 'Temperature': '-',
                            'Index': '0', 'Slot': '-'},
                    'SH0.BAY0': {'Speed': '-', 'Name': 'SH0.BAY0', 'Parent': 'EB-2425P-E6EBD_SHG0998507G4KFD',
                                 'Handle': 'EB-2425P-E6EBD_SHG0998507G4KFD_ses1', 'Voltage': '-', 'Status': 'ok',
                                 'Type': 'drive_bay', 'Identify': 'off', 'Temperature': '-', 'Index': '0', 'Slot': '-'},
                    'CT1': {'Speed': '-', 'Name': 'CT1', 'Parent': 'TUNGPCIB_PCHFS15410070',
                            'Handle': 'TUNGPCIB_PCTFL17340186', 'Voltage': '-', 'Status': 'ok', 'Type': 'controller',
                            'Identify': 'off', 'Temperature': '-', 'Index': '1', 'Slot': '-'}}
        result = hardware_utils.parse_purehw_list(PUREHW_LINES)
        self.assertEqual(result, expected)


class ParseParseFinddriveTestCase(unittest.TestCase):
    """Unit tests for parse_finddrive."""

    with gzip.open(test_utils.get_files_of_type('Uncategorized/finddrive.json')[0]) as json_file:
        json_data = ujson.load(json_file, precise_float=True)

    def test_valid_lines(self):
        """Test parsing valid finddrive output lines."""
        expected = self.json_data
        result = hardware_utils.parse_finddrive(FINDDRIVE_LINES)
        self.assertEqual(result, expected)

    def test_consistent_lengths(self):
        """Ensure that the length of each value is the same."""
        expected_length = 159
        result = hardware_utils.parse_finddrive(FINDDRIVE_LINES)
        for key, value in result.items():
            vlength = len(value)
            msg = 'The length of {} was expected to be {}, got {} instead.'.format(key, vlength, expected_length)
            self.assertEqual(vlength, expected_length, msg=msg)

    def test_bad_line(self):
        """Ensure that we raise a ValueError for a malformed line."""
        bad_lines = [
            # pylint: disable=line-too-long
            '------------------------------------------------------------------------\n',
            '        Drive                  Nodes              Product          Rev                 SN     Expander    Enclosure            Slot\n',
            '     /dev/sg0                    sda  INTEL SSDSCKGW180A4         DC31   CVDA6176004J180H           NA       FA-x70         40186.4\n',
            '\n',
            '        Drive                  Nodes              Product          Rev                 SN     Expander    Enclosure            Slot  Subslot      SAT                  SAT_Rev\n',
            # This following line is missing information.
            ' /dev/nvme7n1                nvme7n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN17436939            -\n',
            '/dev/nvme15n1               nvme15n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN174369A1            -     M_SERIES     10070-CH0.1        -        -                        -\n',
            '/dev/nvme16n1               nvme16n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN174369D6            -     M_SERIES     10070-CH0.2        -        -                        -\n',
            '/dev/nvme14n1               nvme14n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN1743699F            -     M_SERIES     10070-CH0.3        -        -                        -\n',
            '/dev/nvme18n1               nvme18n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN174368F5            -     M_SERIES     10070-CH0.4        -        -                        -\n',
            '/dev/nvme13n1               nvme13n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN17436975            -     M_SERIES     10070-CH0.5        -        -                        -\n',
            '/dev/nvme19n1               nvme19n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN1743699E            -     M_SERIES     10070-CH0.6        -        -                        -\n',
            '/dev/nvme17n1               nvme17n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN17436969            -     M_SERIES     10070-CH0.7        -        -                        -\n',
            '/dev/nvme23n1               nvme23n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN17436936            -     M_SERIES     10070-CH0.8        -        -                        -\n',
            '/dev/nvme21n1               nvme21n1 PURE WSSD7425-00BG008TB08.qp        1.5.2      PFMUN17436937            -     M_SERIES     10070-CH0.9        -        -                        -\n',
            ' /dev/nvme0n1                nvme0n1       PURE NVRAM0101       0.3.10      PNVFS15420184            -     M_SERIES  10070-CH0.NVB0        -        -                        -\n',
            ' /dev/nvme1n1                nvme1n1       PURE NVRAM0101       0.3.10      PNVFS154300F0            -     M_SERIES  10070-CH0.NVB1        -        -                        -\n',
            ' /dev/nvme2n1                nvme2n1       PURE NVRAM0101       0.3.10      PNVFS15420181            -     M_SERIES  10070-CH0.NVB2        -        -                        -\n',
            ' /dev/nvme3n1                nvme3n1       PURE NVRAM0101       0.3.10      PNVFS154100AE            -     M_SERIES  10070-CH0.NVB3        -        -                        -\n',
            '\n',
        ]
        with self.assertRaises(ValueError):
            hardware_utils.parse_finddrive(bad_lines)


class PortTestCase(unittest.TestCase):
    """Unit tests for Port."""

    def test_init(self):
        """Simple test, flesh out once this actually gets used and has methods."""
        port = hardware_utils.Port('ETH0', connected=True, link_speed='10 Mb')
        self.assertTrue(port)
        self.assertEqual(port.link_speed, 10000000.0)

    def test_not_connected(self):
        """Test what happens when it is not connected."""
        port = hardware_utils.Port('ETH0', connected=False, link_speed='10 Mb')
        self.assertFalse(port.connected)
        self.assertEqual(port.link_speed, 0)


class SensorTestCase(unittest.TestCase):
    """Unit tests for Sensor."""

    def test_init(self):
        """Simple test, flesh out once this actually gets used and has methods."""
        sensor = hardware_utils.Sensor('FAN1', status='offline')
        self.assertTrue(sensor)


class StorageGroupTestCase(unittest.TestCase):
    """Unit tests for StorageGroup."""
    drive = drive_utils.SSD('BAY1', 'SH1', capacity='100 PiB')
    drive2 = drive_utils.SSD('BAY2', 'SH1', capacity='1 PiB')
    test_group = DummyStorageGroup('My Group')

    def test_build(self):
        """Test instantiating a StorageGroup."""
        self.assertTrue(self.test_group)

    def test_has_component(self):
        """Unit tests for the has_component method."""
        self.test_group.evac_single_drive('SH1.BAY1')
        self.test_group.add_component(self.drive)
        self.assertTrue(self.test_group.has_component('SH1.BAY1'))

    def test_add_component(self):
        """Unit tests for the add_component method."""
        # Ensure that we have no drives to start with:
        self.test_group.components = {}
        self.test_group.add_component(self.drive)
        self.assertTrue('SH1.BAY1' in self.test_group.components.keys())
        # Now add a non-compatible component:
        ipmi = hardware_utils.IPMI('Test IPMI')
        with self.assertRaises(custom_errors.HardwareCompatibilityError):
            self.test_group.add_component(ipmi)

    def test_evac_single_drive(self):
        """Unit tests for the evac_single_drive method."""
        # Ensure that we have no drives to start with:
        self.test_group.components = {}
        self.test_group.add_component(self.drive)
        self.assertTrue('SH1.BAY1' in self.test_group.components.keys())
        self.test_group.evac_single_drive('SH1.BAY1')
        self.assertEqual(self.test_group.components, {})

    def test_evac_multiple_drives(self):
        """Unit tests for the evac_multiple_drives method."""
        # Ensure that we have no drives to start with:
        self.test_group.components = {}
        self.test_group.add_component(self.drive)
        self.assertTrue('SH1.BAY1' in self.test_group.components.keys())
        self.test_group.add_component(self.drive2)
        self.assertTrue('SH1.BAY2' in self.test_group.components.keys())
        self.test_group.evac_multiple_drives(['SH1.BAY1', 'SH1.BAY2'])
        self.assertEqual(self.test_group.components, {})


if __name__ == '__main__':
    unittest.main()
