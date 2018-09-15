from rpy2.robjects import packages, pandas2ri

def fitzroy():
    # Recommendation from the documentation due to some weirdness around how R packages use these labels internally
    translations = {'package.dependencies': 'package_dot_dependencies',
                    'package_dependencies': 'package_uscore_dependencies'}
    return packages.importr('fitzRoy', robject_translations=translations)

def r_to_pandas(df):
    pandas_df = pandas2ri.ri2py(df)
    r_cols = pandas_df.columns.values
    pandas_df.columns = [x.lower().replace('.', '_') for x in r_cols]

    return pandas_df
