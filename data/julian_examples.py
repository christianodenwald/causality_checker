formulations = {
    "Symmetric Overdetermination": {
        "Structural Equations": [
            "A = 1",
            "B = 1",
            "C = A or B"
        ],
        "Process Algebra": [
            "A_1 = !ac.A_1",
            "B_1 = !bc.B_1",
            "C_0 = (ac + bc).C_1",
            "C_1 = 0"
        ]
    },
    "Conjunction": {
        "Structural Equations": [
            "A = 1",
            "B = 1",
            "C = A and B"
        ],
        "Process Algebra": [
            "A_1 = !ac.A_1",
            "B_1 = !bc.B_1",
            "C_0 = (ac || bc).C_1",
            "C_1 = 0"
        ]
    },
    "Asymmetric Overdetermination": {
        "Structural Equations": [
            "ST = 1",
            "BT = 1",
            "SH = ST",
            "BH = BT and not SH",
            "BS = SH or BH"
        ],
        "Process Algebra": [
            "ST_1 = !stsh.ST_1",
            "BT_1 = !btbh.BT_1",
            "SH_0 = !shbh.SH_0 + stsh.SH_1",
            "SH_1 = !shbs.SH_1",
            "BH_0 = (shbh || btbh).BH_1",
            "BH_1 = !bhbs.BH_1",
            "BS_0 = (shbs + bhbs).BS_1"
        ]
    },
    "Double Prevention": {
        "Structural Equations": [
            "A = 1",
            "B = 1",
            "C = A and not B",
            "D = A and not C"
        ],
        "Process Algebra": [
            "A_1 = !ad.A_1 + !ac.A_1",
            "B_1 = !bc.B_1",
            "C_0 = (ac || bc).C_1 + !cd.C_0",
            "C_1 = 0",
            "D_0 = (ad || cd).D_1"
        ]
    }
}