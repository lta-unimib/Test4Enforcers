import re

import pandas as pd

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

def main():
    flags = []
    flags.append('XposedBridge\.log')

    exclusions = ''.join(map(lambda x: f'(?!{x})', flags))
    pattern = re.compile(r'(\d+):(.+):(.+):(.+):(.+):(\d+):(?:'+ exclusions + r'(.+)|'+ exclusions + r'(.+\s.+)) \|==> (.+)')

    with open('mutants.log') as f:
        lines = f.read()

    groups = []
    matches = pattern.finditer(lines, re.MULTILINE)
    for match in matches:
        if int(match.group(6)) < 370:
            groups.append(match.groups())

    df = pd.DataFrame.from_records(groups, columns=['ID', 'Mutation', 'Original Operator', 'Replacement Operator', 'FQDN', 'Line', 'Content', 'Multiline content', 'Replacement'], index='ID')

    groups = df.groupby(['Mutation'])['Mutation'].agg('count').to_frame('Count').reset_index()
    groups['Relative'] = 100 * groups['Count'] / groups['Count'].sum()
    print(groups)
    print()

    groups = df.groupby(['Mutation', 'Original Operator', 'Replacement Operator'])['Replacement Operator'].agg('count').to_frame('Count').reset_index()
    groups['Relative'] = 100 * groups['Count'] / groups['Count'].sum()
    groups = groups.sort_values(by='Relative', ascending=False)
    print(groups)
    print()

if __name__ == '__main__':
    main()
