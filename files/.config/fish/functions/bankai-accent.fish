function bankai-accent --description "Set this shell's Bleach portrait accents"
    set -g bankai_portrait "$argv[1]"
    set -g bankai_prompt_primary E63946
    set -g bankai_prompt_secondary 65C9FF
    set -g bankai_prompt_label BANKAI
    switch "$argv[1]"
        case jugram
            set -g bankai_prompt_primary E8D9A0
            set -g bankai_prompt_secondary 91DCFF
            set -g bankai_prompt_label JUGRAM
        case bazz-b
            set -g bankai_prompt_primary FF8C72
            set -g bankai_prompt_secondary F0C674
            set -g bankai_prompt_label BAZZ B
        case bambietta
            set -g bankai_prompt_primary D1A5FF
            set -g bankai_prompt_secondary FF8F85
            set -g bankai_prompt_label BAMBIETTA
        case starrk
            set -g bankai_prompt_primary 91B9D9
            set -g bankai_prompt_secondary E8D9A0
            set -g bankai_prompt_label STARRK
        case harribel
            set -g bankai_prompt_primary F0C674
            set -g bankai_prompt_secondary 76E3A3
            set -g bankai_prompt_label HARRIBEL
        case hisagi
            set -g bankai_prompt_primary 83D9C4
            set -g bankai_prompt_secondary C5CFFF
            set -g bankai_prompt_label HISAGI
        case komamura
            set -g bankai_prompt_primary DDA66B
            set -g bankai_prompt_secondary E8EDF5
            set -g bankai_prompt_label KOMAMURA
        case urahara-bankai
            set -g bankai_prompt_primary FF8F85
            set -g bankai_prompt_secondary A8D18D
            set -g bankai_prompt_label "URAHARA BANKAI"
        case renji-bankai
            set -g bankai_prompt_primary FF6270
            set -g bankai_prompt_secondary FFE29A
            set -g bankai_prompt_label "RENJI BANKAI"
        case hitsugaya-bankai
            set -g bankai_prompt_primary D7F3FF
            set -g bankai_prompt_secondary 76D7E8
            set -g bankai_prompt_label "HITSUGAYA BANKAI"
        case yamamoto
            set -g bankai_prompt_primary FFB56B
            set -g bankai_prompt_secondary FFE29A
            set -g bankai_prompt_label "YAMAMOTO"
        case shunsui
            set -g bankai_prompt_primary F2A6CF
            set -g bankai_prompt_secondary E8D9A0
            set -g bankai_prompt_label "SHUNSUI"
        case ukitake
            set -g bankai_prompt_primary B5F5EA
            set -g bankai_prompt_secondary E8EDF5
            set -g bankai_prompt_label "UKITAKE"
        case unohana
            set -g bankai_prompt_primary F2A6CF
            set -g bankai_prompt_secondary FF8F85
            set -g bankai_prompt_label "UNOHANA"
        case mayuri
            set -g bankai_prompt_primary D1A5FF
            set -g bankai_prompt_secondary F0C674
            set -g bankai_prompt_label "MAYURI"
        case soi-fon
            set -g bankai_prompt_primary F0C674
            set -g bankai_prompt_secondary E8EDF5
            set -g bankai_prompt_label "SOI FON"
        case shinji
            set -g bankai_prompt_primary F0C674
            set -g bankai_prompt_secondary FF8F85
            set -g bankai_prompt_label "SHINJI"
        case rangiku
            set -g bankai_prompt_primary FFB56B
            set -g bankai_prompt_secondary F2A6CF
            set -g bankai_prompt_label "RANGIKU"
        case gin
            set -g bankai_prompt_primary C5CFFF
            set -g bankai_prompt_secondary E8EDF5
            set -g bankai_prompt_label "GIN"
        case nelliel
            set -g bankai_prompt_primary 8EE3BE
            set -g bankai_prompt_secondary F2A6CF
            set -g bankai_prompt_label "NELLIEL"
        case yhwach
            set -g bankai_prompt_primary FF8F85
            set -g bankai_prompt_secondary E8D9A0
            set -g bankai_prompt_label "YHWACH"
        case urahara
            set -g bankai_prompt_primary A8D18D
            set -g bankai_prompt_secondary E8D9A0
            set -g bankai_prompt_label URAHARA
        case orihime
            set -g bankai_prompt_primary FFB56B
            set -g bankai_prompt_secondary 91DCFF
            set -g bankai_prompt_label ORIHIME
        case chad
            set -g bankai_prompt_primary FF8F85
            set -g bankai_prompt_secondary EAC8A0
            set -g bankai_prompt_label CHAD
        case uryu
            set -g bankai_prompt_primary 91DCFF
            set -g bankai_prompt_secondary D7F3FF
            set -g bankai_prompt_label URYU
        case renji
            set -g bankai_prompt_primary FF6270
            set -g bankai_prompt_secondary F0C674
            set -g bankai_prompt_label RENJI
        case byakuya
            set -g bankai_prompt_primary F2A6CF
            set -g bankai_prompt_secondary E8EDF5
            set -g bankai_prompt_label BYAKUYA
        case yoruichi
            set -g bankai_prompt_primary C5A0FF
            set -g bankai_prompt_secondary F0C674
            set -g bankai_prompt_label YORUICHI
        case hitsugaya
            set -g bankai_prompt_primary 91DCFF
            set -g bankai_prompt_secondary B5F5EA
            set -g bankai_prompt_label HITSUGAYA
        case kenpachi
            set -g bankai_prompt_primary F0C674
            set -g bankai_prompt_secondary FF8C42
            set -g bankai_prompt_label KENPACHI
        case aizen
            set -g bankai_prompt_primary C5A0FF
            set -g bankai_prompt_secondary E8EDF5
            set -g bankai_prompt_label AIZEN
        case grimmjow
            set -g bankai_prompt_primary 65C9FF
            set -g bankai_prompt_secondary B5F5EA
            set -g bankai_prompt_label GRIMMJOW
        case rukia-bankai
            set -g bankai_prompt_primary D7F3FF
            set -g bankai_prompt_secondary 91DCFF
            set -g bankai_prompt_label RUKIA
        case ulquiorra
            set -g bankai_prompt_primary 76E3A3
            set -g bankai_prompt_secondary B5F5D3
            set -g bankai_prompt_label ULQUIORRA
        case hollow-mask
            set -g bankai_prompt_secondary F0C674
            set -g bankai_prompt_label HOLLOW
        case split-ichigo
            set -g bankai_prompt_primary FF8C42
            set -g bankai_prompt_label 'HALF HOLLOW'
        case vasto-lorde
            set -g bankai_prompt_primary FF6270
            set -g bankai_prompt_secondary FFE29A
            set -g bankai_prompt_label 'VASTO LORDE'
        case dangai-ichigo
            set -g bankai_prompt_primary FF8C42
            set -g bankai_prompt_secondary E8EDF5
            set -g bankai_prompt_label DANGAI
        case mugetsu
            set -g bankai_prompt_primary FF6270
            set -g bankai_prompt_secondary 91DCFF
            set -g bankai_prompt_label MUGETSU
        case white-ichigo
            set -g bankai_prompt_primary E8EDF5
            set -g bankai_prompt_secondary F0C674
            set -g bankai_prompt_label WHITE
    end
    bankai-syntax "$bankai_prompt_primary" "$bankai_prompt_secondary"
end
