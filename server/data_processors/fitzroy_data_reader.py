import pandas as pd
from rpy2.robjects import packages, pandas2ri, vectors


def fitzroy() -> packages.InstalledSTPackage:
    # Recommendation from the documentation due to some weirdness around how
    # R packages use these labels internally
    translations = {'package.dependencies': 'package_dot_dependencies',
                    'package_dependencies': 'package_uscore_dependencies'}
    return packages.importr('fitzRoy', robject_translations=translations)


def r_to_pandas(r_data_frame: vectors.DataFrame) -> pd.DataFrame:
    return pandas2ri.ri2py(r_data_frame).rename(columns=lambda x: x.lower().replace('.', '_'))
