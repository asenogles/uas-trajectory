import numpy as np
import pandas as pd


base = pd.read_csv(r"F:\\CoastalProject\\Hooskanaden\\Fall2019\UAS\\Trajectory\\06_OUT\\LongBase\\Broadcast\\100_0018_Rinex_cameras.txt")
uas = pd.read_csv(r"F:\\CoastalProject\\Hooskanaden\\Fall2019\UAS\\Trajectory\\06_OUT\\UasBase\\Precise\\100_0018_Rinex_cameras.txt")

X = (base["X"] - uas["X"]).to_numpy()
Y = (base["Y"] - uas["Y"]).to_numpy()
Z = (base["Z"] - uas["Z"]).to_numpy()

X = np.abs(X).mean()
Y = np.abs(Y).mean()
Z = np.abs(Z).mean()

print(f"mean difference in X: {X}")
print(f"mean difference in Y: {Y}")
print(f"mean difference in Z: {Z}")