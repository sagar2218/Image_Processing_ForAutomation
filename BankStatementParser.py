import pandas as pd


class BankStatementParser:
    """
    Parses Textract table output specifically for bank/financial statements.
    Converts extracted tables into a clean pandas DataFrame.
    """

    EXPECTED_COLUMNS = ['date', 'description', 'debit', 'credit', 'balance']

    def parse_transactions(self, tables):
        """
        Finds the transaction table among all extracted tables
        and returns a clean DataFrame.
        """
        all_dfs = []

        for table in tables:
            if len(table) < 2:
                continue

            df = pd.DataFrame(table[1:], columns=table[0])  # first row = header

            # Normalize column names
            df.columns = [str(c).lower().strip() for c in df.columns]

            # Score how likely this is the transactions table
            matches = sum(
                any(exp in col for col in df.columns)
                for exp in self.EXPECTED_COLUMNS
            )

            if matches >= 2:
                df = self._clean_dataframe(df)
                all_dfs.append(df)

        return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

    def _clean_dataframe(self, df):
        """Strip whitespace, drop empty rows, normalize amounts."""
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        df = df.dropna(how='all')
        df = df[df.apply(lambda r: r.astype(str).str.strip().ne('').any(), axis=1)]
        return df