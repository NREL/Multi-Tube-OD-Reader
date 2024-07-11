from statistics import linear_regression, correlation
import pandas
import logging
import matplotlib.pyplot as plt
import numpy


df1 = pandas.read_csv("C:/users/shebdon/documents/github/multitubeOD/my_app/new_leds_low_to_high.tsv", delimiter = "\t",header = 4, comment = "#")
df1 = df1.drop(columns = "Temperature")
df2 = df1.copy()



def melted_df_to_plot(df, x_column = "Time (min)"):
    #input long DF. 
    #If df made with unique names, mean = original data, std = NA (not plotted)
    #If unique names replaced with group names, mean = group mean, std = std
    df=df
    summary = df.groupby([x_column, "variable"], as_index=False)["value"].agg({'mean', 'std'}) 
    group_names = list(summary["variable"].drop_duplicates())
    fig, ax = plt.subplots()
    ax.set_ylabel('Optical Density')
    ax.set_xlabel('Time (min)')
    for group in group_names:
        #Plot the mean +/- std of each timepoint
        group_data = summary.loc[summary["variable"] == group]
        x_data = group_data[x_column] 
        y_data = group_data["mean"]
        ymin = group_data["mean"] - group_data["std"]
        ymax = group_data["mean"] + group_data["std"]
        ax.plot(x_data, y_data, label = group)
        ax.fill_between(x_data, ymin, ymax, alpha = 0.2)
    plt.legend()
    return fig


def growth_rates(df, x_column = "Time (min)"):
    """
    df is wide format 
    x:string is name of column for values for x axis
    """
    df=df
    skip_columns = [x_column]
    apply_columns = df.columns.difference(skip_columns)
    df[apply_columns] = df[apply_columns].apply( numpy.log )
    rates = df[apply_columns].apply(lambda vals: numpy.polyfit(df[x_column], vals, 1), result_type='expand')
    return rates



#Make long df of original data
skip_columns = ["Time (min)"]
apply_columns = df2.columns.difference(skip_columns)
df2[apply_columns] = df2[apply_columns].diff().rolling(60).sum()
df2 = df2.melt(id_vars = ["Time (min)"] )


#make long df with group names
df3 = df1.melt(id_vars = ["Time (min)"] )
df3.replace(["Caesar:2", "Caesar:3", "Caesar:4", "Caesar:5"], "Too_bright", inplace = True)
print("df", df1)





"""
melted_df_to_plot(df = df2)
plt.show()
melted_df_to_plot(df = df3)
plt.show()
"""
print(growth_rates(df1))