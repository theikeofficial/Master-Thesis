import os 
from copy import deepcopy

from utils.cnf.instance import \
    collect_cnf_files_and_sizes, \
    calculate_numbers_of_variables_and_clauses, \
    print_number_of_instances_per_category, \
    generate_satzilla_features, \
    generate_edgelist_formats, \
    generate_node2vec_features
from utils.cnf.plot import \
    plot_filesizes, \
    plot_variables_and_clauses_distrubutions, \
    plot_variables_and_clauses_distrubutions_with_limit
from utils.csv.dataframe import \
    save_cnf_zipped_data_to_csv
from utils.os.process import \
    cmd_args


def main():
    bar = '================================================================================'
    print(cmd_args)
    this_directory = os.path.abspath(os.getcwd())
    if cmd_args.wd != '':
        this_directory = os.path.abspath(cmd_args.wd)

    if cmd_args.printCategories or cmd_args.plotFilesizes or cmd_args.plotFilteredData:
        print(bar)
        print('Collecting data about instances per category...')
        inst_dict = print_number_of_instances_per_category(this_directory, ['SAT12-INDU.csv', 'SAT12-HAND.csv'])
        print(bar)
        print('Collecting data about CNF files and sizes...')
        cnf_files, file_sizes, files_not_in_dict, files_not_on_disk = collect_cnf_files_and_sizes(this_directory, inst_dict)
        for file in files_not_on_disk:
            print(file)
    if cmd_args.plotFilesizes:
        print(bar)
        zipped = zip(cnf_files, file_sizes)
        zipped = sorted(zipped, key=lambda t: t[1])
        print('Plotting filesizes...')
        plot_filesizes(this_directory, zipped)
    
    if cmd_args.plotFilteredData:
        print(bar)
        print('Collecting data about CNF files, variables and clauses...')
        zipped, max_vars, max_clauses = calculate_numbers_of_variables_and_clauses(cnf_files)
        zipped = sorted(zipped, key=lambda t: t[1][0])
        print('Plotting and saving filtered data...')
        plot_variables_and_clauses_distrubutions(this_directory, deepcopy(zipped))
        save_cnf_zipped_data_to_csv(deepcopy(zipped), os.path.join(this_directory, 'chosen_data', 'no_limits.csv'))
        limits = [(100, None), (500, None), (1000, None), (5000, None), (500, 200000), (1000, 200000), (5000, 200000), \
            (50000, 1000000)]
        for limit in limits:
            plot_variables_and_clauses_distrubutions_with_limit(this_directory, deepcopy(zipped), limit[0], limit[1])
            filename = os.path.join(this_directory, 'chosen_data', 'max_vars_{0}{1}.csv'.format(limit[0], '' if limit[1] is None else '_max_clauses_{0}'.format(limit[1])))
            save_cnf_zipped_data_to_csv(deepcopy(zipped), filename, limit[0], limit[1])

    if cmd_args.satzilla:
        print(bar)
        print('Generating SATzilla2012 features...')
        generate_satzilla_features('./chosen_data/no_limits.csv')

    if cmd_args.edgelist:
        print(bar)
        print('Generating edgelist formats...')
        generate_edgelist_formats('./chosen_data/max_vars_5000_max_clauses_200000.csv', this_directory)

    if cmd_args.node2vec:
        print(bar)
        print('Generating node2vec features...')
        generate_node2vec_features('./chosen_data/max_vars_5000_max_clauses_200000.csv', this_directory)

    print(bar)

if __name__ == '__main__':
    main()
