# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# pyre-strict

import io
import os
import pkgutil
from datetime import datetime
from typing import cast, List
from unittest import TestCase

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import pytz
from dateutil import parser
from dateutil.relativedelta import relativedelta
from kats.compat.pandas import (
    assert_frame_equal,
    assert_index_equal,
    assert_series_equal,
)
from kats.consts import (
    DEFAULT_TIME_NAME,
    DEFAULT_VALUE_NAME,
    TimeSeriesData,
    TSIterator,
)


def load_data(file_name: str) -> pd.DataFrame:
    ROOT = "kats"
    if "kats" in os.getcwd().lower():
        path = "data/"
    else:
        path = "kats/data/"
    data_object = pkgutil.get_data(ROOT, path + file_name)
    # pyre-fixme[6]: For 1st argument expected `Buffer` but got `Optional[bytes]`.
    return pd.read_csv(io.BytesIO(data_object), encoding="utf8")


TIME_COL_NAME = "ds"
VALUE_COL_NAME = "y"
MULTIVAR_VALUE_DF_COLS: List[str] = [VALUE_COL_NAME, VALUE_COL_NAME + "_1"]

EMPTY_DF = pd.DataFrame()
EMPTY_TIME_SERIES = pd.Series([], name=DEFAULT_TIME_NAME, dtype="datetime64[ns]")
EMPTY_VALUE_SERIES = pd.Series([], name=DEFAULT_VALUE_NAME, dtype=float)
EMPTY_VALUE_SERIES_NO_NAME = pd.Series([], dtype=float)
# pyre-fixme[9]: EMPTY_DF_WITH_COLS has type `DataFrame`; used as `Union[DataFrame,
#  Series]`.
EMPTY_DF_WITH_COLS: pd.DataFrame = pd.concat(
    [EMPTY_TIME_SERIES, EMPTY_VALUE_SERIES], axis=1
)
NUM_YEARS_OFFSET = 12

CAT_TIME_INDEX = pd.Series(pd.date_range("2020-01-01", periods=5))
CAT_VALUE = pd.Series(["a", "b", "c", "d", "e"], name="cat_var")
CAT_MUL_DF = pd.DataFrame(
    {
        "time": CAT_TIME_INDEX,
        "cat_var": CAT_VALUE,
        "num_var": np.arange(5),
    }
)


class TimeSeriesBaseTest(TestCase):
    def setUp(self) -> None:
        # load Dataframes for testing
        self.AIR_DF = load_data("air_passengers.csv")
        self.AIR_DF_DATETIME = self.AIR_DF.copy(deep=True)
        self.AIR_DF_DATETIME.ds = self.AIR_DF_DATETIME.ds.apply(
            lambda x: parser.parse(x)
        )
        self.AIR_DF_UNIXTIME = self.AIR_DF.copy(deep=True)
        self.AIR_DF_UNIXTIME.ds = self.AIR_DF_DATETIME.ds.apply(
            lambda x: (x - datetime(1970, 1, 1)).total_seconds()
        )
        self.AIR_DF_WITH_DEFAULT_NAMES = self.AIR_DF.copy(deep=True)
        self.AIR_DF_WITH_DEFAULT_NAMES.columns = [DEFAULT_TIME_NAME, DEFAULT_VALUE_NAME]
        self.MULTIVAR_AIR_DF = self.AIR_DF.copy(deep=True)
        self.MULTIVAR_AIR_DF[VALUE_COL_NAME + "_1"] = self.MULTIVAR_AIR_DF.y * 2
        self.MULTIVAR_AIR_DF_DATETIME = self.MULTIVAR_AIR_DF.copy(deep=True)
        self.MULTIVAR_AIR_DF_DATETIME.ds = self.MULTIVAR_AIR_DF_DATETIME.ds.apply(
            lambda x: parser.parse(x)
        )
        self.MULTIVAR_VALUE_DF = self.MULTIVAR_AIR_DF[MULTIVAR_VALUE_DF_COLS]
        self.AIR_TIME_SERIES = self.AIR_DF.ds
        self.AIR_TIME_SERIES_PD_DATETIME = pd.to_datetime(self.AIR_TIME_SERIES)
        # pyre-fixme[16]: `Timestamp` has no attribute `apply`.
        self.AIR_TIME_SERIES_UNIXTIME = self.AIR_TIME_SERIES_PD_DATETIME.apply(
            lambda x: (x - datetime(1970, 1, 1)).total_seconds()
        )
        self.AIR_VALUE_SERIES = self.AIR_DF[VALUE_COL_NAME]
        self.AIR_TIME_DATETIME_INDEX = pd.DatetimeIndex(self.AIR_TIME_SERIES)


class TimeSeriesDataInitTest(TimeSeriesBaseTest):
    def setUp(self) -> None:
        super(TimeSeriesDataInitTest, self).setUp()
        # Univariate TimeSeriesData initialized from a pd.DataFrame
        self.ts_from_df = TimeSeriesData(df=self.AIR_DF, time_col_name=TIME_COL_NAME)
        # Univariate TimeSeriesData initialized from a pd.DataFrame with time
        # as a datetime.datetime object
        self.ts_from_df_datetime = TimeSeriesData(
            df=self.AIR_DF_DATETIME, time_col_name=TIME_COL_NAME
        )
        # Univariate TimeSeriesData initialized from a pd.DataFrame with time
        # as unix time
        self.ts_from_df_with_unix = TimeSeriesData(
            df=self.AIR_DF_UNIXTIME,
            use_unix_time=True,
            unix_time_units="s",
            time_col_name=TIME_COL_NAME,
        )
        # Multivariate TimeSeriesData initialized from a pd.DataFrame
        self.ts_from_df_multi = TimeSeriesData(
            df=self.MULTIVAR_AIR_DF, time_col_name=TIME_COL_NAME
        )
        # Multivariate TimeSeriesData initialized from a pd.DataFrame with time
        # as a datetime.datetime object
        self.ts_from_df_multi_datetime = TimeSeriesData(
            df=self.MULTIVAR_AIR_DF_DATETIME, time_col_name=TIME_COL_NAME
        )
        # Univariate TimeSeriesData initialized from two pd.Series with time
        # as a string
        self.ts_from_series_univar_no_datetime = TimeSeriesData(
            time=self.AIR_TIME_SERIES, value=self.AIR_VALUE_SERIES
        )
        # Univariate TimeSeriesData initialized from two pd.Series with time
        # as a pd.Timestamp
        self.ts_from_series_univar_with_datetime = TimeSeriesData(
            time=self.AIR_TIME_SERIES_PD_DATETIME, value=self.AIR_VALUE_SERIES
        )
        # Univariate TimeSeriesData initialized from two pd.Series with time
        # as unix time
        self.ts_from_series_with_unix = TimeSeriesData(
            time=self.AIR_TIME_SERIES_UNIXTIME,
            value=self.AIR_VALUE_SERIES,
            use_unix_time=True,
            unix_time_units="s",
            time_col_name=TIME_COL_NAME,
        )
        # Univariate TimeSeriesData initialized with time as a pd.Series and
        # value as a pd.DataFrame
        self.ts_from_series_and_df_univar = TimeSeriesData(
            time=self.AIR_TIME_SERIES, value=self.AIR_VALUE_SERIES.to_frame()
        )
        # Multivariate TimeSeriesData initialized from a pd.Series for time
        # and DataFrame for value
        self.ts_from_series_and_df_multivar = TimeSeriesData(
            time=self.AIR_TIME_SERIES, value=self.MULTIVAR_VALUE_DF
        )
        # Univariate TimeSeriesData initialized with time as a pd.DateTimeIndex
        # and value as a pd.Series
        self.ts_from_index_and_series_univar = TimeSeriesData(
            time=self.AIR_TIME_DATETIME_INDEX,
            value=self.AIR_VALUE_SERIES,
            time_col_name=TIME_COL_NAME,
        )
        # Multivariate TimeSeriesData initialized with time as a
        # pd.DateTimeIndex and value as a pd.DataFrame
        self.ts_from_index_and_series_multivar = TimeSeriesData(
            time=self.AIR_TIME_DATETIME_INDEX,
            value=self.MULTIVAR_VALUE_DF,
            time_col_name=TIME_COL_NAME,
        )
        # TimeSeriesData initialized from None Objects
        self.ts_df_none = TimeSeriesData(df=None)
        self.ts_time_none_and_value_none = TimeSeriesData(time=None, value=None)
        # TimeSeriesData initialized from Empty Objects
        self.ts_df_empty = TimeSeriesData(df=EMPTY_DF)
        self.ts_time_empty_value_empty = TimeSeriesData(
            time=EMPTY_TIME_SERIES, value=EMPTY_VALUE_SERIES
        )
        self.ts_time_empty_value_empty_no_name = TimeSeriesData(
            time=EMPTY_TIME_SERIES, value=EMPTY_VALUE_SERIES_NO_NAME
        )
        self.ts_time_empty_value_empty_df = TimeSeriesData(
            time=EMPTY_TIME_SERIES, value=EMPTY_DF
        )
        self.ts_time_empty_value_empty_df_with_cols = TimeSeriesData(
            time=EMPTY_TIME_SERIES, value=EMPTY_DF_WITH_COLS
        )

        # univariate data with missing time
        self.ts_univariate_missing = TimeSeriesData(
            df=pd.DataFrame(
                {
                    "time": ["2010-01-01", "2010-01-02", "2010-01-03", "2010-01-05"],
                    "value": [1, 2, 3, 4],
                }
            )
        )

        # multivariate data with missing time
        self.ts_multi_missing = TimeSeriesData(
            df=pd.DataFrame(
                {
                    "time": ["2010-01-01", "2010-01-02", "2010-01-03", "2010-01-05"],
                    "value1": [1, 2, 3, 4],
                    "value2": [4, 3, 2, 1],
                }
            )
        )

        # univariate data with unixtime in US/Pacific with time zone
        self.unix_list = (
            (
                pd.date_range(
                    "2020-03-01", "2020-03-10", tz="US/Pacific", freq="1d"
                ).astype(int)
                / 1e9
            )
            .astype(int)
            .to_list()
        )
        self.ts_univar_PST_tz = TimeSeriesData(
            df=pd.DataFrame({"time": self.unix_list, "value": [0] * 10}),
            use_unix_time=True,
            unix_time_units="s",
            tz="US/Pacific",
        )
        # multivariate data with unixtime in US/Pacific with time zone
        self.ts_multi_PST_tz = TimeSeriesData(
            df=pd.DataFrame(
                {"time": self.unix_list, "value1": [0] * 10, "value2": [0] * 10}
            ),
            use_unix_time=True,
            unix_time_units="s",
            tz="US/Pacific",
        )
        # univariate data with unixtime in US/Pacific without time zone
        self.ts_univar_PST = TimeSeriesData(
            df=pd.DataFrame({"time": self.unix_list, "value": [0] * 10}),
            use_unix_time=True,
            unix_time_units="s",
        )
        # univariate data with date str with tz
        date = ["2020-10-31", "2020-11-01", "2020-11-02"]
        self.ts_univar_str_date_tz = TimeSeriesData(
            df=pd.DataFrame({"time": date, "value": [0] * 3}),
            date_format="%Y-%m-%d",
            tz="US/Pacific",
        )
        # univariate data with date str without tz
        self.ts_univar_str_date = TimeSeriesData(
            df=pd.DataFrame({"time": date, "value": [0] * 3}),
            date_format="%Y-%m-%d",
        )

        # univariate data with date str without tz
        self.ts_multi_str_date = TimeSeriesData(
            df=pd.DataFrame({"time": date, "value1": [0] * 3, "value2": [0] * 3}),
            date_format="%Y-%m-%d",
        )

        # univariate data in US/Pacific Time Zone with missing data
        self.ts_univar_PST_missing_tz = TimeSeriesData(
            df=pd.DataFrame(
                {"time": (self.unix_list[0:4] + self.unix_list[7:10]), "value": [0] * 7}
            ),
            use_unix_time=True,
            unix_time_units="s",
            tz="US/Pacific",
        )

        # test ambiguous
        self.tsd_dst_ambiguous = TimeSeriesData(
            df=pd.DataFrame(
                {
                    "time": [
                        "2022-11-06 00:00:00",
                        "2022-11-06 00:30:00",
                        "2022-11-06 01:00:00",
                        "2022-11-06 01:30:00",
                        "2022-11-06 01:00:00",
                        "2022-11-06 01:30:00",
                        "2022-11-06 02:00:00",
                        "2022-11-06 02:30:00",
                        "2022-11-06 03:00:00",
                        "2022-11-06 03:30:00",
                        "2022-11-06 04:00:00",
                        "2022-11-06 04:30:00",
                    ],
                    "value": [0] * 12,
                }
            ),
            sort_by_time=False,
        )

        # test nonexistent
        self.tsd_dst_nonexistent = TimeSeriesData(
            df=pd.DataFrame(
                {
                    "time": [
                        "2020-03-08 02:00:00",
                        "2020-03-08 02:30:00",
                        "2020-03-08 03:00:00",
                    ],
                    "value": [0] * 3,
                }
            ),
            sort_by_time=False,
        )

    def test_init_categorical_ts(self) -> None:
        # univariate categorical data
        _ = TimeSeriesData(
            time=CAT_TIME_INDEX,
            value=CAT_VALUE,
            categorical_var=["cat_var"],
        )
        # multivariate categorical data
        _ = TimeSeriesData(
            df=CAT_MUL_DF,
            categorical_var=["cat_var"],
        )
        # fail to initialize a TimeSeriesData object with categorical variable if not specified
        self.assertRaises(
            ValueError,
            TimeSeriesData,
            time=CAT_TIME_INDEX,
            value=CAT_VALUE,
        )
        # fail to initialize a TimeSeriesData object with categorical variable if not specified
        self.assertRaises(ValueError, TimeSeriesData, df=CAT_MUL_DF)

    # Testing univariate time series intialized from a DataFrame
    def test_init_from_df_univar(self) -> None:
        # DataFrame with string time
        assert_series_equal(self.ts_from_df.time, self.AIR_TIME_SERIES_PD_DATETIME)
        assert_series_equal(
            cast(pd.Series, self.ts_from_df.value), self.AIR_VALUE_SERIES
        )
        # DataFrame with datetime time
        assert_series_equal(
            self.ts_from_df_datetime.time, self.AIR_TIME_SERIES_PD_DATETIME
        )
        assert_series_equal(
            cast(pd.Series, self.ts_from_df_datetime.value), self.AIR_VALUE_SERIES
        )
        # DataFrame with unix time
        assert_series_equal(
            self.ts_from_df_with_unix.time, self.AIR_TIME_SERIES_PD_DATETIME
        )
        assert_series_equal(
            cast(pd.Series, self.ts_from_df_with_unix.value), self.AIR_VALUE_SERIES
        )

    # Testing multivariate time series initialized from a DataFrame
    def test_init_from_df_multi(self) -> None:
        assert_series_equal(
            self.ts_from_df_multi.time, self.AIR_TIME_SERIES_PD_DATETIME
        )
        assert_frame_equal(
            cast(pd.DataFrame, self.ts_from_df_multi.value), self.MULTIVAR_VALUE_DF
        )

    # Testing univariate time series initialized from a Series and Series/DataFrame
    def test_init_from_series_univar(self) -> None:
        # time and value from Series, with time as string
        assert_series_equal(
            self.ts_from_series_univar_no_datetime.time,
            self.AIR_TIME_SERIES_PD_DATETIME,
        )
        # time and value from Series, with time as pd.Timestamp
        assert_series_equal(
            self.ts_from_series_univar_with_datetime.time,
            self.AIR_TIME_SERIES_PD_DATETIME,
        )
        assert_series_equal(
            cast(pd.Series, self.ts_from_series_univar_no_datetime.value),
            self.AIR_VALUE_SERIES,
        )
        # time and value from Series, with time out of order and `sort_by_time=True`
        unsorted_df = self.AIR_DF.sample(frac=1)
        resorted_ts = TimeSeriesData(
            time=unsorted_df.ds,
            value=unsorted_df.y,
            time_col_name=TIME_COL_NAME,
            sort_by_time=True,
        )
        self.assertEqual(resorted_ts, self.ts_from_df)
        # time and value from Series, with time as unix time
        assert_series_equal(
            self.ts_from_series_with_unix.time, self.AIR_TIME_SERIES_PD_DATETIME
        )
        assert_series_equal(
            cast(pd.Series, self.ts_from_series_with_unix.value), self.AIR_VALUE_SERIES
        )
        # time from Series and value from DataFrame
        assert_series_equal(
            self.ts_from_series_and_df_univar.time, self.AIR_TIME_SERIES_PD_DATETIME
        )
        print(type(self.ts_from_series_and_df_univar.value))
        assert_series_equal(
            cast(pd.Series, self.ts_from_series_and_df_univar.value),
            self.AIR_VALUE_SERIES,
        )

    # Testing multivariate time series initialized from a Series/DataFrame
    def test_init_from_series_multivar(self) -> None:
        # Testing multivariate time series initialized from a
        assert_series_equal(
            self.ts_from_series_and_df_multivar.time, self.AIR_TIME_SERIES_PD_DATETIME
        )
        assert_frame_equal(
            cast(pd.DataFrame, self.ts_from_series_and_df_multivar.value),
            self.MULTIVAR_VALUE_DF,
        )

    # Testing univariate time series with time initialized as a
    # pd.DateTimeIndex
    def test_init_from_index_univar(self) -> None:
        assert_series_equal(
            self.ts_from_index_and_series_univar.time, self.AIR_TIME_SERIES_PD_DATETIME
        )
        assert_series_equal(
            cast(pd.Series, self.ts_from_index_and_series_univar.value),
            self.AIR_VALUE_SERIES,
        )

    # Testing multivariate time series with time initialized as a
    # pd.DateTimeIndex
    def test_init_from_index_multivar(self) -> None:
        assert_series_equal(
            self.ts_from_index_and_series_multivar.time,
            self.AIR_TIME_SERIES_PD_DATETIME,
        )
        assert_frame_equal(
            cast(pd.DataFrame, self.ts_from_index_and_series_multivar.value),
            self.MULTIVAR_VALUE_DF,
        )

    # Testing initialization from None Objects
    def test_none(self) -> None:
        # Testing initialization from None DataFrame
        assert_series_equal(self.ts_df_none.time, EMPTY_TIME_SERIES)
        assert_series_equal(cast(pd.Series, self.ts_df_none.value), EMPTY_VALUE_SERIES)
        # Testing initialization from two None Series
        assert_series_equal(self.ts_time_none_and_value_none.time, EMPTY_TIME_SERIES)
        assert_series_equal(
            cast(pd.Series, self.ts_time_none_and_value_none.value), EMPTY_VALUE_SERIES
        )

    # Testing initialization from Empty Objects
    def test_empty(self) -> None:
        # Testing intialization from empty DataFrame
        assert_series_equal(self.ts_df_empty.time, EMPTY_TIME_SERIES)
        assert_series_equal(cast(pd.Series, self.ts_df_empty.value), EMPTY_VALUE_SERIES)
        # Testing intialization from two empty Series
        assert_series_equal(self.ts_time_empty_value_empty.time, EMPTY_TIME_SERIES)
        assert_series_equal(
            cast(pd.Series, self.ts_time_empty_value_empty.value), EMPTY_VALUE_SERIES
        )
        # Testing intialization from two empty no name Series
        assert_series_equal(
            self.ts_time_empty_value_empty_no_name.time, EMPTY_TIME_SERIES
        )
        assert_series_equal(
            cast(pd.Series, self.ts_time_empty_value_empty_no_name.value),
            EMPTY_VALUE_SERIES,
        )

        # Make sure the time and value objects here have the default names
        self.assertEqual(
            self.ts_time_empty_value_empty_no_name.time.name, DEFAULT_TIME_NAME
        )
        self.assertEqual(
            self.ts_time_empty_value_empty_no_name.value.name, DEFAULT_VALUE_NAME
        )

        # Testing initialization from time as empty Series and value as empty
        # DataFrame
        assert_series_equal(self.ts_time_empty_value_empty_df.time, EMPTY_TIME_SERIES)
        assert_series_equal(
            cast(pd.Series, self.ts_time_empty_value_empty_df.value), EMPTY_VALUE_SERIES
        )
        # Testing initialization from time as empty Series and value as empty
        # DataFrame
        assert_series_equal(
            self.ts_time_empty_value_empty_df_with_cols.time, EMPTY_TIME_SERIES
        )
        assert_series_equal(
            cast(pd.Series, self.ts_time_empty_value_empty_df_with_cols.value),
            EMPTY_VALUE_SERIES,
        )

    # Testing incorrect initializations
    def test_incorrect_init_types(self) -> None:
        # Incorrect initialization with DF
        with self.assertRaises(ValueError):
            # pyre-fixme[6]: Expected `Optional[pd.core.frame.DataFrame]` for 1st
            #  param but got `List[Variable[_T]]`.
            TimeSeriesData(df=[])

        # Incorrect initialization with value
        with self.assertRaises(ValueError):
            TimeSeriesData(time=self.AIR_TIME_SERIES, value=None)
        with self.assertRaises(ValueError):
            # pyre-fixme[6]: Expected `Union[None, pd.core.frame.DataFrame,
            #  pd.core.series.Series]` for 2nd param but got `List[Variable[_T]]`.
            TimeSeriesData(time=self.AIR_TIME_SERIES, value=[])

        # Incorrect initialization with time
        with self.assertRaises(ValueError):
            TimeSeriesData(time=None, value=self.AIR_VALUE_SERIES)
        with self.assertRaises(ValueError):
            # pyre-fixme[6]: Expected `Union[None,
            #  pd.core.indexes.datetimes.DatetimeIndex, pd.core.series.Series]` for 1st
            #  param but got `List[Variable[_T]]`.
            TimeSeriesData(time=[], value=self.AIR_VALUE_SERIES)

        # Incorrect initialization with time and value
        with self.assertRaises(ValueError):
            # pyre-fixme[6]: Expected `Union[None,
            #  pd.core.indexes.datetimes.DatetimeIndex, pd.core.series.Series]` for 1st
            #  param but got `List[Variable[_T]]`.
            TimeSeriesData(time=[], value=[])

        # Incorrect initialization with value dtypes
        with self.assertRaises(ValueError):
            TimeSeriesData(
                time=self.AIR_TIME_SERIES, value=self.AIR_VALUE_SERIES.map(str)
            )
        with self.assertRaises(ValueError):
            TimeSeriesData(
                time=self.AIR_TIME_SERIES, value=self.MULTIVAR_VALUE_DF.applymap(str)
            )

    # Testing incorrect initializations
    def test_incorrect_init_lengths(self) -> None:
        # Incorrect initialization with different length time and values
        with self.assertRaises(ValueError):
            TimeSeriesData(time=self.AIR_TIME_SERIES, value=self.AIR_VALUE_SERIES[:-1])
        with self.assertRaises(ValueError):
            TimeSeriesData(time=self.AIR_TIME_SERIES[:-1], value=self.AIR_VALUE_SERIES)
        with self.assertRaises(ValueError):
            TimeSeriesData(time=self.AIR_TIME_SERIES, value=self.MULTIVAR_VALUE_DF[:-1])
        with self.assertRaises(ValueError):
            TimeSeriesData(time=self.AIR_TIME_SERIES[:-1], value=self.MULTIVAR_VALUE_DF)

    # Testing DataFrame conversion
    def test_to_dataframe(self) -> None:
        # Univariate case
        assert_frame_equal(self.ts_from_df.to_dataframe(), self.AIR_DF_DATETIME)
        # Multivariate case
        assert_frame_equal(
            self.ts_from_df_multi_datetime.to_dataframe(), self.MULTIVAR_AIR_DF_DATETIME
        )
        # Series Cases
        assert_frame_equal(
            self.ts_from_series_univar_no_datetime.to_dataframe(), self.AIR_DF_DATETIME
        )
        assert_frame_equal(
            self.ts_from_series_univar_with_datetime.to_dataframe(),
            self.AIR_DF_DATETIME,
        )
        # Series/DataFrame Cases
        assert_frame_equal(
            self.ts_from_series_and_df_univar.to_dataframe(), self.AIR_DF_DATETIME
        )
        assert_frame_equal(
            self.ts_from_series_and_df_multivar.to_dataframe(),
            self.MULTIVAR_AIR_DF_DATETIME,
        )
        # Empty/None Cases
        assert_frame_equal(self.ts_df_none.to_dataframe(), EMPTY_DF_WITH_COLS)
        assert_frame_equal(
            self.ts_time_none_and_value_none.to_dataframe(), EMPTY_DF_WITH_COLS
        )
        assert_frame_equal(self.ts_df_empty.to_dataframe(), EMPTY_DF_WITH_COLS)
        assert_frame_equal(
            self.ts_time_empty_value_empty.to_dataframe(), EMPTY_DF_WITH_COLS
        )
        assert_frame_equal(
            self.ts_time_empty_value_empty_df.to_dataframe(), EMPTY_DF_WITH_COLS
        )

    # Testing Data Interpolate
    def test_interpolate(self) -> None:
        # univariate
        self.assertEqual(
            self.ts_univariate_missing.interpolate(freq="D", method="linear"),
            TimeSeriesData(
                pd.DataFrame(
                    {
                        "time": [
                            "2010-01-01",
                            "2010-01-02",
                            "2010-01-03",
                            "2010-01-04",
                            "2010-01-05",
                        ],
                        "value": [1, 2, 3, 3.5, 4],
                    }
                )
            ),
        )

        self.assertEqual(
            self.ts_univariate_missing.interpolate(freq="D", method="ffill"),
            TimeSeriesData(
                pd.DataFrame(
                    {
                        "time": [
                            "2010-01-01",
                            "2010-01-02",
                            "2010-01-03",
                            "2010-01-04",
                            "2010-01-05",
                        ],
                        "value": [1, 2, 3, 3, 4],
                    }
                )
            ),
        )

        self.assertEqual(
            self.ts_univariate_missing.interpolate(freq="D", method="bfill"),
            TimeSeriesData(
                pd.DataFrame(
                    {
                        "time": [
                            "2010-01-01",
                            "2010-01-02",
                            "2010-01-03",
                            "2010-01-04",
                            "2010-01-05",
                        ],
                        "value": [1, 2, 3, 4, 4],
                    }
                )
            ),
        )

        # check pd.interpolate method that is not explicitly defined in TimeSeriesData code
        self.assertEqual(
            self.ts_univariate_missing.interpolate(freq="D", method="nearest"),
            TimeSeriesData(
                pd.DataFrame(
                    {
                        "time": [
                            "2010-01-01",
                            "2010-01-02",
                            "2010-01-03",
                            "2010-01-04",
                            "2010-01-05",
                        ],
                        "value": [1, 2, 3, 3, 4],
                    }
                )
            ),
        )

        # check pd.interpolate method that is not explicitly defined in TimeSeriesData code
        # and has additional parameters
        self.assertEqual(
            self.ts_univariate_missing.interpolate(
                freq="D", method="polynomial", order=3
            ),
            TimeSeriesData(
                pd.DataFrame(
                    {
                        "time": [
                            "2010-01-01",
                            "2010-01-02",
                            "2010-01-03",
                            "2010-01-04",
                            "2010-01-05",
                        ],
                        "value": [1, 2, 3, 3.75, 4],
                    }
                )
            ),
        )

        # check pd.interpolate method that is not explicitly defined in TimeSeriesData code
        # and has additional parameters
        self.assertEqual(
            self.ts_univariate_missing.interpolate(
                freq="D", method="polynomial", order=1
            ),
            TimeSeriesData(
                pd.DataFrame(
                    {
                        "time": [
                            "2010-01-01",
                            "2010-01-02",
                            "2010-01-03",
                            "2010-01-04",
                            "2010-01-05",
                        ],
                        "value": [1, 2, 3, 3.5, 4],
                    }
                )
            ),
        )

        # check method that is not in pd.interpolate and have not explicitly defined in TimeSeriesData code
        with self.assertRaises(ValueError):
            self.ts_univariate_missing.interpolate(
                freq="D", method="bad_input_should_fail"
            )

        # multivariate
        self.assertEqual(
            self.ts_multi_missing.interpolate(freq="D", method="linear"),
            TimeSeriesData(
                pd.DataFrame(
                    {
                        "time": [
                            "2010-01-01",
                            "2010-01-02",
                            "2010-01-03",
                            "2010-01-04",
                            "2010-01-05",
                        ],
                        "value1": [1, 2, 3, 3.5, 4],
                        "value2": [4, 3, 2, 1.5, 1],
                    }
                )
            ),
        )

        self.assertEqual(
            self.ts_multi_missing.interpolate(freq="D", method="ffill"),
            TimeSeriesData(
                pd.DataFrame(
                    {
                        "time": [
                            "2010-01-01",
                            "2010-01-02",
                            "2010-01-03",
                            "2010-01-04",
                            "2010-01-05",
                        ],
                        "value1": [1, 2, 3, 3, 4],
                        "value2": [4, 3, 2, 2, 1],
                    }
                )
            ),
        )

        self.assertEqual(
            self.ts_multi_missing.interpolate(freq="D", method="bfill"),
            TimeSeriesData(
                pd.DataFrame(
                    {
                        "time": [
                            "2010-01-01",
                            "2010-01-02",
                            "2010-01-03",
                            "2010-01-04",
                            "2010-01-05",
                        ],
                        "value1": [1, 2, 3, 4, 4],
                        "value2": [4, 3, 2, 1, 1],
                    }
                )
            ),
        )

        # test with no frequency given univariate
        self.assertEqual(
            self.ts_univariate_missing.interpolate(method="linear"),
            TimeSeriesData(
                pd.DataFrame(
                    {
                        "time": [
                            "2010-01-01",
                            "2010-01-02",
                            "2010-01-03",
                            "2010-01-04",
                            "2010-01-05",
                        ],
                        "value": [1, 2, 3, 3.5, 4],
                    }
                )
            ),
        )

        # no frequency given, for multivariate
        self.assertEqual(
            self.ts_multi_missing.interpolate(method="linear"),
            TimeSeriesData(
                pd.DataFrame(
                    {
                        "time": [
                            "2010-01-01",
                            "2010-01-02",
                            "2010-01-03",
                            "2010-01-04",
                            "2010-01-05",
                        ],
                        "value1": [1, 2, 3, 3.5, 4],
                        "value2": [4, 3, 2, 1.5, 1],
                    }
                )
            ),
        )

        # test methods that are not explicitly defined in TimeSeriesData
        self.assertEqual(
            self.ts_multi_missing.interpolate(method="time"),
            TimeSeriesData(
                pd.DataFrame(
                    {
                        "time": [
                            "2010-01-01",
                            "2010-01-02",
                            "2010-01-03",
                            "2010-01-04",
                            "2010-01-05",
                        ],
                        "value1": [1, 2, 3, 3.5, 4],
                        "value2": [4, 3, 2, 1.5, 1],
                    }
                )
            ),
        )

        # test methods that are not explicitly defined in TimeSeriesData
        # with additional arguments
        self.assertEqual(
            self.ts_multi_missing.interpolate(method="polynomial", order=3),
            TimeSeriesData(
                pd.DataFrame(
                    {
                        "time": [
                            "2010-01-01",
                            "2010-01-02",
                            "2010-01-03",
                            "2010-01-04",
                            "2010-01-05",
                        ],
                        "value1": [1, 2, 3, 3.75, 4],
                        "value2": [4, 3, 2, 1.25, 1],
                    }
                )
            ),
        )

        # check method that is not in pd.interpolate and have not explicitly defined in TimeSeriesData code
        with self.assertRaises(ValueError):
            self.ts_multi_missing.interpolate(freq="D", method="bad_input_should_fail")

    # Testing Data interpolate with base
    def test_interpolate_base(self) -> None:
        # create time series with missing data
        np.random.seed(0)
        x = np.random.normal(0.5, 3, 998)
        time_val0 = list(
            pd.date_range(start="2018-02-03 14:59:59", freq="1800s", periods=1000)
        )
        time_val = time_val0[:300] + time_val0[301:605] + time_val0[606:]
        ts0 = TimeSeriesData(pd.DataFrame({"time": time_val, "value": pd.Series(x)}))

        # calculate frequency first
        frequency = str(int(ts0.infer_freq_robust().total_seconds())) + "s"

        # Without base value, interpolate won't work, will return all NaN
        # this is because start time is not from "**:00:00" or "**:30:00" type.
        # This is equivalent to origin="start_day"
        self.assertEqual(
            # pyre-fixme[16]: Optional type has no attribute `value`.
            ts0.interpolate(freq=frequency).to_dataframe().fillna(0).value.sum(),
            0,
        )
        # With base value, will start from "**:59:59" ("**:00:00" - 1 sec)
        # or "**:29:59" ("**:30:00" -1 sec).
        # Here we default to origin="start" instead of origin="start_day", which works.
        self.assertEqual(
            ts0.interpolate(freq=frequency, base=-1).to_dataframe().isna().value.sum(),
            0,
        )

        # second example, base = 4
        time_val0 = list(
            pd.date_range(start="2018-02-03 14:00:04", freq="1800s", periods=1000)
        )
        time_val = time_val0[:300] + time_val0[301:605] + time_val0[606:]
        ts0 = TimeSeriesData(pd.DataFrame({"time": time_val, "value": pd.Series(x)}))

        frequency = str(int(ts0.infer_freq_robust().total_seconds())) + "s"

        self.assertEqual(
            ts0.interpolate(freq=frequency).to_dataframe().fillna(0).value.sum(),
            0,
        )
        self.assertEqual(
            ts0.interpolate(freq=frequency, base=4).to_dataframe().isna().value.sum(),
            0,
        )

    def test_to_array(self) -> None:
        # Univariate case
        np.testing.assert_array_equal(
            self.ts_from_df.to_array(), self.AIR_DF_DATETIME.to_numpy()
        )
        # Multivariate case
        np.testing.assert_array_equal(
            self.ts_from_df_multi_datetime.to_array(),
            self.MULTIVAR_AIR_DF_DATETIME.to_numpy(),
        )
        # Series Cases
        np.testing.assert_array_equal(
            self.ts_from_series_univar_no_datetime.to_array(),
            self.AIR_DF_DATETIME.to_numpy(),
        )
        np.testing.assert_array_equal(
            self.ts_from_series_univar_with_datetime.to_array(),
            self.AIR_DF_DATETIME.to_numpy(),
        )
        # Series/DataFrame Cases
        np.testing.assert_array_equal(
            self.ts_from_series_and_df_univar.to_array(),
            self.AIR_DF_DATETIME.to_numpy(),
        )
        np.testing.assert_array_equal(
            self.ts_from_series_and_df_multivar.to_array(),
            self.MULTIVAR_AIR_DF_DATETIME.to_numpy(),
        )
        # Empty/None Cases
        np.testing.assert_array_equal(self.ts_df_none.to_array(), np.empty)
        np.testing.assert_array_equal(
            self.ts_time_none_and_value_none.to_array(), np.empty
        )
        np.testing.assert_array_equal(self.ts_df_empty.to_array(), np.empty)
        np.testing.assert_array_equal(
            self.ts_time_empty_value_empty.to_array(), np.empty
        )
        np.testing.assert_array_equal(
            self.ts_time_empty_value_empty_df.to_array(), np.empty
        )

    def test_tz(self) -> None:
        self.ts_univar_PST_tz.validate_data(
            validate_frequency=True, validate_dimension=True
        )
        self.assertEqual(self.ts_univar_PST_tz.freq_to_timedelta(), pd.Timedelta("1d"))
        self.assertEqual(self.ts_univar_PST_tz.tz(), pytz.timezone("US/Pacific"))
        self.assertTrue(
            (
                np.array(self.unix_list)
                == (self.ts_univar_PST_tz.time.values.astype(int) / 1e9).astype(int)
            ).all()
        )

        with self.assertRaisesRegex(
            ValueError, "Only constant frequency is supported for time!"
        ):
            self.ts_univar_PST.validate_data(
                validate_frequency=True, validate_dimension=True
            )

        self.ts_univar_str_date.validate_data(
            validate_frequency=True, validate_dimension=True
        )
        self.assertEqual(
            self.ts_univar_str_date.freq_to_timedelta(), pd.Timedelta("1d")
        )

        self.ts_univar_str_date_tz.validate_data(
            validate_frequency=True, validate_dimension=True
        )
        self.assertEqual(
            self.ts_univar_str_date_tz.freq_to_timedelta(), pd.Timedelta("1d")
        )
        self.assertEqual(self.ts_univar_PST_tz.tz(), pytz.timezone("US/Pacific"))

        # test ambiguous
        tsd = TimeSeriesData(
            df=pd.DataFrame(
                {
                    "time": [
                        "2018-10-28 01:30:00",
                        "2018-10-28 02:00:00",
                        "2018-10-28 02:30:00",
                        "2018-10-28 02:00:00",
                        "2018-10-28 02:30:00",
                        "2018-10-28 03:00:00",
                        "2018-10-28 03:30:00",
                    ],
                    "value": [0] * 7,
                }
            ),
            tz="CET",
            tz_ambiguous="infer",
        )
        tsd.validate_data(validate_frequency=True, validate_dimension=True)

        # test nonexistent
        tsd = TimeSeriesData(
            df=pd.DataFrame(
                {
                    "time": [
                        "2020-03-08 02:00:00",
                        "2020-03-08 02:30:00",
                        "2020-03-08 03:00:00",
                    ],
                    "value": [0] * 3,
                }
            ),
            tz="US/Pacific",
            tz_nonexistent="shift_forward",
        )

    def test_infer_freq_robust(self) -> None:
        self.assertEqual(
            self.ts_univariate_missing.infer_freq_robust(),
            pd.Timedelta(value=1, unit="D"),
        )

        self.assertEqual(
            self.ts_univar_PST_missing_tz.infer_freq_robust(),
            pd.Timedelta(value=1, unit="D"),
        )

    def test_is_data_missing(self) -> None:
        self.assertEqual(self.ts_univariate_missing.is_data_missing(), True)

        self.assertEqual(self.ts_univar_PST_missing_tz.is_data_missing(), True)

        self.assertEqual(self.ts_from_series_and_df_univar.is_data_missing(), False)

        self.assertEqual(self.ts_from_series_and_df_multivar.is_data_missing(), False)

    def test_is_timezone_aware(self) -> None:
        self.assertEqual(self.ts_univar_PST_tz.is_timezone_aware(), True)

        self.assertEqual(self.ts_univar_str_date.is_timezone_aware(), False)

        self.assertEqual(self.ts_multi_PST_tz.is_timezone_aware(), True)

        self.assertEqual(self.ts_multi_str_date.is_timezone_aware(), False)

    def test_set_timezone(self) -> None:
        ts_local = self.ts_univar_str_date
        self.assertEqual(ts_local.is_timezone_aware(), False)
        ts_local.set_timezone(tz="US/Eastern")
        self.assertEqual(ts_local.is_timezone_aware(), True)
        # pyre-fixme[16]: `DatetimeIndex` has no attribute `tzinfo`.
        self.assertEqual(str(pd.DatetimeIndex(ts_local.time).tzinfo), "US/Eastern")

        ts_local = self.ts_multi_str_date
        self.assertEqual(ts_local.is_timezone_aware(), False)
        ts_local.set_timezone(tz="US/Pacific")
        self.assertEqual(ts_local.is_timezone_aware(), True)
        self.assertEqual(str(pd.DatetimeIndex(ts_local.time).tzinfo), "US/Pacific")

        ts_local = self.tsd_dst_ambiguous
        self.assertEqual(ts_local.is_timezone_aware(), False)
        ts_local.set_timezone(tz="US/Eastern", tz_ambiguous="infer", sort_by_time=True)
        self.assertEqual(ts_local.is_timezone_aware(), True)
        self.assertEqual(str(pd.DatetimeIndex(ts_local.time).tzinfo), "US/Eastern")

        ts_local = self.tsd_dst_nonexistent
        self.assertEqual(ts_local.is_timezone_aware(), False)
        ts_local.set_timezone(
            tz="US/Pacific", tz_nonexistent="shift_forward", sort_by_time=True
        )
        self.assertEqual(ts_local.is_timezone_aware(), True)
        self.assertEqual(str(pd.DatetimeIndex(ts_local.time).tzinfo), "US/Pacific")

    def test_convert_timezone(self) -> None:
        ts_local = self.ts_univar_PST_tz
        # pyre-fixme[16]: `DatetimeIndex` has no attribute `tzinfo`.
        self.assertEqual(str(pd.DatetimeIndex(ts_local.time).tzinfo), "US/Pacific")
        ts_local.convert_timezone(tz="US/Eastern")
        self.assertEqual(str(pd.DatetimeIndex(ts_local.time).tzinfo), "US/Eastern")

        ts_local = self.ts_multi_PST_tz
        self.assertEqual(str(pd.DatetimeIndex(ts_local.time).tzinfo), "US/Pacific")
        ts_local.convert_timezone(tz="US/Eastern")
        self.assertEqual(str(pd.DatetimeIndex(ts_local.time).tzinfo), "US/Eastern")

    def test_min_max_values(self) -> None:
        # test min/max value for univariate
        self.assertEqual(self.ts_from_df.min, np.nanmin(self.ts_from_df.value.values))
        self.assertEqual(self.ts_from_df.max, np.nanmax(self.ts_from_df.value.values))

        # test min/max value for multivariate
        self.assertEqual(
            # pyre-fixme[16]: `float` has no attribute `equals`.
            self.ts_from_df_multi.min.equals(
                self.ts_from_df_multi.value.min(skipna=True)
            ),
            True,
        )
        self.assertEqual(
            # pyre-fixme[16]: Item `float` of `Union[float, Series]` has no
            #  attribute `equals`.
            self.ts_from_df_multi.max.equals(
                self.ts_from_df_multi.value.max(skipna=True)
            ),
            True,
        )

        # test min/max value for empty TS
        empty_ts = TimeSeriesData(pd.DataFrame())
        self.assertEqual(np.isnan(empty_ts.min), True)
        self.assertEqual(np.isnan(empty_ts.max), True)

        # test if min/max changes if values are re-assigned for univariate
        ts_from_df_new = TimeSeriesData(df=self.AIR_DF, time_col_name=TIME_COL_NAME)
        new_val = np.random.randn(len(self.AIR_DF))
        ts_from_df_new.value = pd.Series(new_val)
        self.assertEqual(ts_from_df_new.min, np.min(new_val))
        self.assertEqual(ts_from_df_new.max, np.max(new_val))

        # test if min/max changes if values are re-assigned with NaNs for univariate
        new_val[-1] = np.nan
        ts_from_df_new.value = pd.Series(new_val)
        self.assertEqual(ts_from_df_new.min, np.nanmin(new_val))
        self.assertEqual(ts_from_df_new.max, np.nanmax(new_val))

        # test min/max changes if values are re-assigned for multivariate
        ts_from_df_multi_new = TimeSeriesData(
            self.MULTIVAR_AIR_DF, time_col_name=TIME_COL_NAME
        )
        new_val_multi = np.random.randn(
            self.MULTIVAR_VALUE_DF.shape[0], self.MULTIVAR_VALUE_DF.shape[1] - 1
        )
        ts_from_df_multi_new.value = pd.DataFrame(new_val_multi)
        self.assertEqual(
            # pyre-fixme[16]: Item `float` of `Union[float, Series]` has no
            #  attribute `equals`.
            ts_from_df_multi_new.min.equals(pd.DataFrame(new_val_multi).min()),
            True,
        )
        self.assertEqual(
            # pyre-fixme[16]: Item `float` of `Union[float, Series]` has no
            #  attribute `equals`.
            ts_from_df_multi_new.max.equals(pd.DataFrame(new_val_multi).max()),
            True,
        )

        # test min/max changes if values are re-assigned with NaNs for multivariate
        new_val_multi[0] = np.nan
        ts_from_df_multi_new.value = pd.DataFrame(new_val_multi)
        self.assertEqual(
            # pyre-fixme[16]: Item `float` of `Union[float, Series]` has no
            #  attribute `equals`.
            ts_from_df_multi_new.min.equals(
                pd.DataFrame(new_val_multi).min(skipna=True)
            ),
            True,
        )
        self.assertEqual(
            # pyre-fixme[16]: Item `float` of `Union[float, Series]` has no
            #  attribute `equals`.
            ts_from_df_multi_new.max.equals(
                pd.DataFrame(new_val_multi).max(skipna=True)
            ),
            True,
        )


class TimeSeriesDataOpsTest(TimeSeriesBaseTest):
    def setUp(self) -> None:
        super(TimeSeriesDataOpsTest, self).setUp()
        # Creating DataFrames
        # DataFrame with date offset
        transformed_df_date = self.AIR_DF_DATETIME.copy(deep=True)
        transformed_df_date.ds = transformed_df_date.ds.apply(
            lambda x: x + relativedelta(years=NUM_YEARS_OFFSET)
        )
        transformed_df_date_concat = pd.concat(
            [self.AIR_DF, transformed_df_date], ignore_index=True
        )
        transformed_df_date_double = self.AIR_DF_DATETIME.copy(deep=True)
        transformed_df_date_double.ds = transformed_df_date.ds.apply(
            lambda x: x + relativedelta(years=NUM_YEARS_OFFSET * 2)
        )
        transformed_df_date_concat_double = pd.concat(
            [self.AIR_DF, transformed_df_date_double], ignore_index=True
        )
        # DataFrames with value offset
        transformed_df_value = self.AIR_DF.copy(deep=True)
        transformed_df_value.y = transformed_df_value.y.apply(lambda x: x * 2)
        transformed_df_value_inv = self.AIR_DF.copy(deep=True)
        transformed_df_value_inv.y = transformed_df_value_inv.y.apply(lambda x: x * -1)
        # DataFrame with date and value offset
        transformed_df_date_and_value = transformed_df_date.copy(deep=True)
        transformed_df_date_and_value.y = transformed_df_date_and_value.y.apply(
            lambda x: x * 2
        )
        # DataFrame with date offset (multivariate)
        transformed_df_date_multi = transformed_df_date.copy(deep=True)
        transformed_df_date_multi[VALUE_COL_NAME + "_1"] = (
            transformed_df_date_multi.y * 2
        )
        transformed_df_date_concat_multi = pd.concat(
            [self.MULTIVAR_AIR_DF, transformed_df_date_multi], ignore_index=True
        )
        transformed_df_date_concat_mixed = pd.concat(
            [self.MULTIVAR_AIR_DF_DATETIME, transformed_df_date]
        )
        transformed_df_date_double_multi = transformed_df_date_double.copy(deep=True)
        transformed_df_date_double_multi[VALUE_COL_NAME + "_1"] = (
            transformed_df_date_double_multi.y * 2
        )
        transformed_df_date_concat_double_multi = pd.concat(
            [self.MULTIVAR_AIR_DF, transformed_df_date_double_multi], ignore_index=True
        )
        transformed_df_date_concat_double_mixed = pd.concat(
            [self.MULTIVAR_AIR_DF_DATETIME, transformed_df_date_double]
        )
        # DataFrame with value offset (multivariate)
        transformed_df_value_none_multi = self.MULTIVAR_AIR_DF.copy(deep=True)
        transformed_df_value_none_multi.y = transformed_df_value_none_multi.y_1
        transformed_df_value_none_multi.y_1 = np.nan
        # DataFrame with date and value offset (multivariate)
        transformed_df_date_and_value_multi = transformed_df_date_and_value.copy(
            deep=True
        )
        transformed_df_date_and_value_multi[VALUE_COL_NAME + "_1"] = (
            transformed_df_date_and_value_multi.y * 2
        )
        # DataFrame with all constant values
        df_zeros = self.AIR_DF.copy(deep=True)
        df_zeros.y.values[:] = 0
        df_ones = self.AIR_DF.copy(deep=True)
        df_ones.y.values[:] = 1
        df_twos = df_ones.copy(deep=True)
        df_twos.y.values[:] = 2
        df_neg_ones = self.AIR_DF.copy(deep=True)
        df_neg_ones.y.values[:] = -1
        df_ones_multi = df_ones.copy(deep=True)
        df_ones_multi[VALUE_COL_NAME + "_1"] = df_ones_multi.y * 2

        # Creating TimeSeriesData objects
        # Univariate TimeSeriesData initialized from a pd.DataFrame
        self.ts_univ_1 = TimeSeriesData(df=self.AIR_DF, time_col_name=TIME_COL_NAME)
        self.ts_univ_2 = TimeSeriesData(df=self.AIR_DF, time_col_name=TIME_COL_NAME)
        self.ts_univ_default_names = TimeSeriesData(df=self.AIR_DF_WITH_DEFAULT_NAMES)
        self.ts_univ_default_names_2 = TimeSeriesData(df=self.AIR_DF_WITH_DEFAULT_NAMES)

        # Multivariate TimeSeriesData initialized from a pd.DataFrame
        self.ts_multi_1 = TimeSeriesData(
            df=self.MULTIVAR_AIR_DF, time_col_name=TIME_COL_NAME
        )
        self.ts_multi_2 = TimeSeriesData(
            df=self.MULTIVAR_AIR_DF, time_col_name=TIME_COL_NAME
        )

        # TimeSeriesData with date offset
        self.ts_date_transform_univ = TimeSeriesData(
            df=transformed_df_date, time_col_name=TIME_COL_NAME
        )
        self.ts_date_transform_concat_univ = TimeSeriesData(
            df=transformed_df_date_concat, time_col_name=TIME_COL_NAME
        )
        self.ts_date_transform_double_univ = TimeSeriesData(
            df=transformed_df_date_double, time_col_name=TIME_COL_NAME
        )
        self.ts_date_transform_concat_double_univ = TimeSeriesData(
            df=transformed_df_date_concat_double, time_col_name=TIME_COL_NAME
        )
        # TimeSeriesData with date offset (multivariate)
        self.ts_date_transform_multi = TimeSeriesData(
            df=transformed_df_date_multi, time_col_name=TIME_COL_NAME
        )
        self.ts_date_transform_concat_multi = TimeSeriesData(
            df=transformed_df_date_concat_multi, time_col_name=TIME_COL_NAME
        )
        self.ts_date_transform_concat_mixed = TimeSeriesData(
            df=transformed_df_date_concat_mixed, time_col_name=TIME_COL_NAME
        )
        self.ts_date_transform_double_multi = TimeSeriesData(
            df=transformed_df_date_double_multi, time_col_name=TIME_COL_NAME
        )
        self.ts_date_transform_concat_double_multi = TimeSeriesData(
            df=transformed_df_date_concat_double_multi, time_col_name=TIME_COL_NAME
        )
        self.ts_date_transform_concat_double_mixed = TimeSeriesData(
            df=transformed_df_date_concat_double_mixed, time_col_name=TIME_COL_NAME
        )
        # TimeSeriesData with value offset
        self.ts_value_transform_univ = TimeSeriesData(
            df=transformed_df_value, time_col_name=TIME_COL_NAME
        )
        self.ts_value_transform_inv_univ = TimeSeriesData(
            df=transformed_df_value_inv, time_col_name=TIME_COL_NAME
        )
        # TimeSeriesData with value offset (multivariate)
        self.ts_value_transform_none_multi = TimeSeriesData(
            df=transformed_df_value_none_multi, time_col_name=TIME_COL_NAME
        )
        # TimeSeriesData with date and value offset
        self.ts_date_and_value_transform_univ = TimeSeriesData(
            df=transformed_df_date_and_value, time_col_name=TIME_COL_NAME
        )
        # TimeSeriesData with date and value offset (multivariate)
        self.ts_date_and_value_transform_multi = TimeSeriesData(
            df=transformed_df_date_and_value_multi, time_col_name=TIME_COL_NAME
        )
        # TimeSeriesData object with all constant values
        self.ts_zero = TimeSeriesData(df=df_zeros, time_col_name=TIME_COL_NAME)
        self.ts_ones = TimeSeriesData(df=df_ones, time_col_name=TIME_COL_NAME)
        self.ts_twos = TimeSeriesData(df=df_twos, time_col_name=TIME_COL_NAME)
        self.ts_neg_ones = TimeSeriesData(df=df_neg_ones, time_col_name=TIME_COL_NAME)
        self.ts_ones_multi = TimeSeriesData(
            df=df_ones_multi, time_col_name=TIME_COL_NAME
        )
        # Empty TimeSeriesData Object
        self.ts_empty = TimeSeriesData(df=EMPTY_DF)
        self.ts_empty_with_cols = TimeSeriesData(
            df=EMPTY_DF_WITH_COLS, time_col_name=TIME_COL_NAME
        )
        # Copies for Extended objects
        self.ts_univ_extend = TimeSeriesData(
            df=self.AIR_DF, time_col_name=TIME_COL_NAME
        )
        self.ts_univ_extend_2 = TimeSeriesData(
            df=self.AIR_DF, time_col_name=TIME_COL_NAME
        )
        self.ts_univ_extend_err = TimeSeriesData(
            df=self.AIR_DF, time_col_name=TIME_COL_NAME
        )
        self.ts_multi_extend = TimeSeriesData(
            df=self.MULTIVAR_AIR_DF, time_col_name=TIME_COL_NAME
        )
        self.ts_multi_extend_2 = TimeSeriesData(
            df=self.MULTIVAR_AIR_DF, time_col_name=TIME_COL_NAME
        )
        self.ts_multi_extend_3 = TimeSeriesData(
            df=self.MULTIVAR_AIR_DF, time_col_name=TIME_COL_NAME
        )
        self.ts_multi_extend_4 = TimeSeriesData(
            df=self.MULTIVAR_AIR_DF, time_col_name=TIME_COL_NAME
        )
        self.ts_multi_extend_err = TimeSeriesData(
            df=self.MULTIVAR_AIR_DF, time_col_name=TIME_COL_NAME
        )
        self.ts_multi_extend_err_2 = TimeSeriesData(
            df=self.MULTIVAR_AIR_DF, time_col_name=TIME_COL_NAME
        )
        self.ts_empty_extend = TimeSeriesData(df=EMPTY_DF)
        self.ts_empty_extend_err = TimeSeriesData(df=EMPTY_DF)

        # Other values
        self.length = len(self.AIR_DF)

        self.tsd_exclude_test = TimeSeriesData(
            df=pd.DataFrame(
                {
                    "time": [
                        "2018-10-28 01:30:00",
                        "2018-10-28 02:00:00",
                        "2018-10-28 02:30:00",
                        "2018-10-28 03:00:00",
                        "2018-10-28 03:30:00",
                        "2018-10-28 04:00:00",
                        "2018-10-28 04:30:00",
                    ],
                    "value": [0] * 7,
                }
            ),
            tz="UTC",
        )

    def test_eq(self) -> None:
        # Univariate equality
        self.assertTrue(self.ts_univ_1 == self.ts_univ_2)
        # Multivariate equality
        self.assertTrue(self.ts_multi_1 == self.ts_multi_2)
        # Univariate inequality
        self.assertFalse(self.ts_univ_1 == self.ts_date_transform_univ)
        self.assertFalse(self.ts_univ_1 == self.ts_value_transform_univ)
        self.assertFalse(self.ts_univ_1 == self.ts_date_and_value_transform_univ)
        # Multivariate inequality
        self.assertFalse(self.ts_multi_1 == self.ts_date_transform_multi)
        self.assertFalse(self.ts_multi_1 == self.ts_value_transform_none_multi)
        self.assertFalse(self.ts_multi_1 == self.ts_date_and_value_transform_multi)
        # Univariate vs. Multivariate inequality
        self.assertFalse(self.ts_univ_1 == self.ts_multi_1)
        self.assertFalse(self.ts_multi_1 == self.ts_univ_1)

    def test_ne(self) -> None:
        # Univariate equality
        self.assertFalse(self.ts_univ_1 != self.ts_univ_2)
        # Multivariate equality
        self.assertFalse(self.ts_multi_1 != self.ts_multi_2)
        # Univariate inequality
        self.assertTrue(self.ts_univ_1 != self.ts_date_transform_univ)
        self.assertTrue(self.ts_univ_1 != self.ts_value_transform_univ)
        self.assertTrue(self.ts_univ_1 != self.ts_date_and_value_transform_univ)
        # Multivariate inequality
        self.assertTrue(self.ts_multi_1 != self.ts_date_transform_multi)
        self.assertTrue(self.ts_multi_1 != self.ts_value_transform_none_multi)
        self.assertTrue(self.ts_multi_1 != self.ts_date_and_value_transform_multi)
        # Univariate vs. Multivariate inequality
        self.assertTrue(self.ts_univ_1 != self.ts_multi_1)
        self.assertTrue(self.ts_multi_1 != self.ts_univ_1)

    def test_add(self) -> None:
        # Add same DataFrames
        self.assertEqual(self.ts_univ_1 + self.ts_univ_2, self.ts_value_transform_univ)
        # Add different DataFrames
        self.assertEqual(
            self.ts_univ_1 + self.ts_value_transform_inv_univ, self.ts_zero
        )
        # Add Univariate and Multivariate DataFrames
        self.assertEqual(
            self.ts_univ_1 + self.ts_multi_1, self.ts_value_transform_none_multi
        )
        # Empty Case
        self.assertEqual(self.ts_empty + self.ts_empty, self.ts_empty)
        # Add DataFrames with different dates
        with self.assertRaises(ValueError):
            self.ts_univ_1 + self.ts_date_transform_univ

    def test_sub(self) -> None:
        # Subtract same DataFrames
        self.assertEqual(self.ts_univ_1 - self.ts_univ_2, self.ts_zero)
        # Subtract different DataFrames
        self.assertEqual(
            self.ts_univ_1 - self.ts_value_transform_inv_univ,
            self.ts_value_transform_univ,
        )
        # Subtract Univariate and Multivariate DataFrames
        self.assertEqual(
            self.ts_multi_1 - self.ts_value_transform_inv_univ,
            self.ts_value_transform_none_multi,
        )
        # Empty Case
        self.assertEqual(self.ts_empty - self.ts_empty, self.ts_empty)
        # Subtract DataFrames with different dates
        with self.assertRaises(ValueError):
            self.ts_univ_1 - self.ts_date_transform_univ

    def test_div(self) -> None:
        # Divide same DataFrames
        self.assertEqual(self.ts_univ_1 / self.ts_univ_2, self.ts_ones)
        # Divide different DataFrames
        self.assertEqual(
            self.ts_univ_1 / self.ts_value_transform_inv_univ, self.ts_neg_ones
        )
        # Divide Univariate and Multivariate DataFrames
        self.assertEqual(
            self.ts_value_transform_univ / self.ts_ones_multi,
            self.ts_value_transform_none_multi,
        )
        # Empty Case
        self.assertEqual(self.ts_empty / self.ts_empty, self.ts_empty)
        # Divide DataFrames with different dates
        with self.assertRaises(ValueError):
            self.ts_univ_1 / self.ts_date_transform_univ

    def test_mul(self) -> None:
        # Multiply same DataFrames
        self.assertEqual(self.ts_ones * self.ts_ones, self.ts_ones)
        # Multiply different DataFrames
        self.assertEqual(self.ts_univ_1 * self.ts_twos, self.ts_value_transform_univ)
        # Multiply Univariate and Multivariate DataFrames
        self.assertEqual(
            self.ts_multi_1 * self.ts_twos, self.ts_value_transform_none_multi
        )
        # Empty Case
        self.assertEqual(self.ts_empty * self.ts_empty, self.ts_empty)
        # Multiply DataFrames with different dates
        with self.assertRaises(ValueError):
            self.ts_univ_1 * self.ts_date_transform_univ

    def test_len(self) -> None:
        # Normal case
        self.assertEqual(len(self.ts_univ_1), self.length)
        # Empty case
        self.assertEqual(len(self.ts_empty), 0)

    def test_empty(self) -> None:
        # Empty case
        self.assertTrue(self.ts_empty.is_empty())
        # Not empty case
        self.assertFalse(self.ts_univ_1.is_empty())

    def test_extend(self) -> None:
        # Testing cases with validate=True
        # Univariate case
        self.ts_univ_extend.extend(self.ts_date_transform_univ)
        self.assertEqual(self.ts_univ_extend, self.ts_date_transform_concat_univ)
        # Multivariate case
        self.ts_multi_extend.extend(self.ts_date_transform_multi)
        self.assertEqual(self.ts_multi_extend, self.ts_date_transform_concat_multi)
        # Univariate and multivariate case
        self.ts_multi_extend_2.extend(self.ts_date_transform_univ)
        self.assertEqual(self.ts_multi_extend_2, self.ts_date_transform_concat_mixed)
        # Empty case
        self.ts_univ_default_names.extend(self.ts_empty)
        self.assertEqual(self.ts_univ_default_names, self.ts_univ_default_names_2)
        # Catching errors
        with self.assertRaises(ValueError):
            self.ts_univ_extend_err.extend(self.ts_date_transform_double_univ)
            # Multivariate case
            self.ts_multi_extend_err.extend(self.ts_date_transform_double_multi)
            # Univariate and multivariate case
            self.ts_multi_extend_err_2.extend(self.ts_date_transform_double_univ)
            # Empty case
            self.ts_empty_extend_err.extend(self.ts_empty)
        # Testing cases with validate=False
        # Univariate case
        self.ts_univ_extend_2.extend(self.ts_date_transform_double_univ, validate=False)
        self.assertEqual(
            self.ts_univ_extend_2, self.ts_date_transform_concat_double_univ
        )
        # Multivariate case
        self.ts_multi_extend_3.extend(
            self.ts_date_transform_double_multi, validate=False
        )
        self.assertEqual(
            self.ts_multi_extend_3, self.ts_date_transform_concat_double_multi
        )
        # Univariate and multivariate case
        self.ts_multi_extend_4.extend(
            self.ts_date_transform_double_univ, validate=False
        )
        self.assertEqual(
            self.ts_multi_extend_4, self.ts_date_transform_concat_double_mixed
        )
        # Empty case
        self.ts_empty_extend.extend(self.ts_empty, validate=False)
        self.assertEqual(self.ts_empty_extend, self.ts_empty)

    def test_exclude_whole_ts(self) -> None:
        tsd_exclude = self.tsd_exclude_test.exclude(
            self.tsd_exclude_test.time.min(), self.tsd_exclude_test.time.max()
        )
        self.assertEqual(tsd_exclude.is_empty(), True)

    def test_exclude_starting_range(self) -> None:
        tsd_after_exclude = self.tsd_exclude_test.exclude(
            self.tsd_exclude_test.time.min(),
            pd.to_datetime("2018-10-28 03:00:00", utc=True),
        )
        expected_result = TimeSeriesData(
            df=pd.DataFrame(
                {
                    "time": [
                        "2018-10-28 03:30:00",
                        "2018-10-28 04:00:00",
                        "2018-10-28 04:30:00",
                    ],
                    "value": [0] * 3,
                }
            ),
            tz="UTC",
        )
        self.assertEqual(tsd_after_exclude, expected_result)

    def test_exclude_ending_range(self) -> None:
        tsd_after_exclude = self.tsd_exclude_test.exclude(
            pd.to_datetime("2018-10-28 02:30:00", utc=True),
            self.tsd_exclude_test.time.max(),
        )
        expected_result = TimeSeriesData(
            df=pd.DataFrame(
                {
                    "time": [
                        "2018-10-28 01:30:00",
                        "2018-10-28 02:00:00",
                    ],
                    "value": [0] * 2,
                }
            ),
            tz="UTC",
        )
        self.assertEqual(tsd_after_exclude, expected_result)

    def test_exclude_middle_range(self) -> None:
        tsd_after_exclude = self.tsd_exclude_test.exclude(
            pd.to_datetime("2018-10-28 02:30:00", utc=True),
            pd.to_datetime("2018-10-28 04:00:00", utc=True),
        )
        expected_result = TimeSeriesData(
            df=pd.DataFrame(
                {
                    "time": [
                        "2018-10-28 01:30:00",
                        "2018-10-28 02:00:00",
                        "2018-10-28 04:30:00",
                    ],
                    "value": [0] * 3,
                }
            ),
            tz="UTC",
        )
        self.assertEqual(tsd_after_exclude, expected_result)

    def test_get_item(self) -> None:
        # Univariate test case
        self.assertEqual(
            self.ts_date_transform_concat_univ[: len(self.ts_univ_1)], self.ts_univ_1
        )
        # Multivariate test case
        self.assertEqual(
            self.ts_date_transform_concat_multi[: len(self.ts_multi_1)], self.ts_multi_1
        )
        # Multivariate test case where we select a specific column
        for col in self.ts_date_transform_concat_multi.value.columns:
            ts_univ = TimeSeriesData(
                time=self.ts_date_transform_concat_multi.time,
                value=self.ts_date_transform_concat_multi.value[col],
                time_col_name=self.ts_date_transform_concat_multi.time_col_name,
            )
            self.assertEqual(self.ts_date_transform_concat_multi[col], ts_univ)
        # Multivariate test case where we select multiple columns
        self.assertEqual(
            self.ts_date_transform_concat_multi[MULTIVAR_VALUE_DF_COLS],
            self.ts_date_transform_concat_multi,
        )
        # Full/Empty cases
        self.assertEqual(self.ts_univ_1[:], self.ts_univ_1)
        self.assertEqual(
            self.ts_univ_1[0:0],
            TimeSeriesData(
                time=pd.Series(name=TIME_COL_NAME),
                value=pd.Series(name=VALUE_COL_NAME),
                time_col_name=TIME_COL_NAME,
            ),
        )

    # pyre-fixme[56]: Pyre was not able to infer the type of the decorator
    #  `pytest.mark.mpl_image_compare`.
    @pytest.mark.mpl_image_compare
    def test_plot(self) -> plt.Figure:
        # Univariate test case
        ax = self.ts_univ_1.plot(cols=["y"])
        self.assertIsNotNone(ax)
        return plt.gcf()

    # pyre-fixme[56]: Pyre was not able to infer the type of the decorator
    #  `pytest.mark.mpl_image_compare`.
    @pytest.mark.mpl_image_compare
    def test_plot_multivariate(self) -> plt.Figure:
        # Multivariate test case
        ax = self.ts_multi_1.plot()
        self.assertIsNotNone(ax)
        return plt.gcf()

    # pyre-fixme[56]: Pyre was not able to infer the type of the decorator
    #  `pytest.mark.mpl_image_compare`.
    @pytest.mark.mpl_image_compare
    def test_plot_params(self) -> plt.Figure:
        # Test more parameter overrides.
        ax = self.ts_multi_1.plot(
            figsize=(8, 3), plot_kwargs={"cmap": "Purples"}, grid=False
        )
        self.assertIsNotNone(ax)
        return plt.gcf()

    # pyre-fixme[56]: Pyre was not able to infer the type of the decorator
    #  `pytest.mark.mpl_image_compare`.
    @pytest.mark.mpl_image_compare
    def test_plot_grid_ax(self) -> plt.Figure:
        # Test grid and ax parameter overrides.
        fig, ax = plt.subplots(figsize=(6, 4))
        ax = self.ts_univ_1.plot(ax=ax, grid_kwargs={"lw": 2, "ls": ":"})
        self.assertIsNotNone(ax)
        return fig

    def test_plot_missing_column(self) -> None:
        # Columns not in data.
        with self.assertRaises(ValueError):
            self.ts_univ_1.plot(cols=["z"])

    def test_plot_empty(self) -> None:
        # No data to plot.
        with self.assertRaises(ValueError):
            self.ts_empty.plot()


class TimeSeriesDataMiscTest(TimeSeriesBaseTest):
    def setUp(self) -> None:
        super(TimeSeriesDataMiscTest, self).setUp()
        # Creating TimeSeriesData objects
        # Univariate TimeSeriesData initialized from a pd.DataFrame
        self.ts_univ = TimeSeriesData(df=self.AIR_DF, time_col_name=TIME_COL_NAME)
        # Multivariate TimeSeriesData initialized from a pd.DataFrame
        self.ts_multi = TimeSeriesData(
            df=self.MULTIVAR_AIR_DF, time_col_name=TIME_COL_NAME
        )

    def test_is_univariate(self) -> None:
        # Univariate case
        self.assertTrue(self.ts_univ.is_univariate())
        # Multivariate case
        self.assertFalse(self.ts_multi.is_univariate())

    def test_time_to_index(self) -> None:
        # Univariate case
        assert_index_equal(self.ts_univ.time_to_index(), self.AIR_TIME_DATETIME_INDEX)
        # Multivariate case
        assert_index_equal(self.ts_multi.time_to_index(), self.AIR_TIME_DATETIME_INDEX)

    def test_repr(self) -> None:
        # Univariate case
        self.assertEqual(self.ts_univ.__repr__(), self.AIR_DF_DATETIME.__repr__())
        # Multivariate case
        self.assertEqual(
            self.ts_multi.__repr__(), self.MULTIVAR_AIR_DF_DATETIME.__repr__()
        )

    def test_repr_html(self) -> None:
        # Univariate case
        self.assertEqual(self.ts_univ._repr_html_(), self.AIR_DF_DATETIME._repr_html_())
        # Multivariate case
        self.assertEqual(
            self.ts_multi._repr_html_(), self.MULTIVAR_AIR_DF_DATETIME._repr_html_()
        )


class TSIteratorTest(TestCase):
    def test_ts_iterator_univariate_next(self) -> None:
        df = pd.DataFrame(
            [["2020-03-01", 100], ["2020-03-02", 120], ["2020-03-03", 130]],
            columns=["time", "y"],
        )
        kats_data = TimeSeriesData(df=df)
        kats_iterator = TSIterator(kats_data)
        val = next(kats_iterator)
        assert_series_equal(
            val.time, pd.Series([pd.Timestamp("2020-03-01")]), check_names=False
        )
        assert_series_equal(
            cast(pd.Series, val.value), pd.Series([100]), check_names=False
        )
        val = next(kats_iterator)
        assert_series_equal(
            val.time, pd.Series([pd.Timestamp("2020-03-02")]), check_names=False
        )
        assert_series_equal(
            cast(pd.Series, val.value), pd.Series([120]), check_names=False
        )
        val = next(kats_iterator)
        assert_series_equal(
            val.time, pd.Series([pd.Timestamp("2020-03-03")]), check_names=False
        )
        assert_series_equal(
            cast(pd.Series, val.value), pd.Series([130]), check_names=False
        )

    def test_ts_iterator_multivariate_next(self) -> None:
        df = pd.DataFrame(
            [
                ["2020-03-01", 100, 200],
                ["2020-03-02", 120, 220],
                ["2020-03-03", 130, 230],
            ],
            columns=["time", "y1", "y2"],
        )
        kats_data = TimeSeriesData(df=df)
        kats_iterator = TSIterator(kats_data)
        val = next(kats_iterator)
        assert_series_equal(
            val.time, pd.Series([pd.Timestamp("2020-03-01")]), check_names=False
        )
        assert_frame_equal(
            cast(pd.DataFrame, val.value),
            pd.DataFrame([[100, 200]], columns=["y1", "y2"]),
        )
        val = next(kats_iterator)
        assert_series_equal(
            val.time, pd.Series([pd.Timestamp("2020-03-02")]), check_names=False
        )
        assert_frame_equal(
            cast(pd.DataFrame, val.value),
            pd.DataFrame([[120, 220]], columns=["y1", "y2"]),
        )
        val = next(kats_iterator)
        assert_series_equal(
            val.time, pd.Series([pd.Timestamp("2020-03-03")]), check_names=False
        )
        assert_frame_equal(
            cast(pd.DataFrame, val.value),
            pd.DataFrame([[130, 230]], columns=["y1", "y2"]),
        )

    def test_ts_iterator_comprehension(self) -> None:
        kats_data = TimeSeriesData(
            time=pd.to_datetime(
                np.array([1596225347, 1596225348, 1596225349]), unit="s", utc=True
            ),
            value=pd.Series(np.array([1, 2, 4])),
        )
        kats_iterator = TSIterator(kats_data)
        kats_list = list(kats_iterator)
        val = kats_list[0]
        assert_series_equal(
            val.time,
            pd.Series([pd.Timestamp("2020-07-31 19:55:47+0000", tz="UTC")]),
            check_names=False,
        )
        assert_series_equal(
            cast(pd.Series, val.value), pd.Series([1]), check_names=False
        )
        val = kats_list[1]
        assert_series_equal(
            val.time,
            pd.Series([pd.Timestamp("2020-07-31 19:55:48+0000", tz="UTC")]),
            check_names=False,
        )
        assert_series_equal(
            cast(pd.Series, val.value), pd.Series([2]), check_names=False
        )
        val = kats_list[2]
        assert_series_equal(
            val.time,
            pd.Series([pd.Timestamp("2020-07-31 19:55:49+0000", tz="UTC")]),
            check_names=False,
        )
        assert_series_equal(
            cast(pd.Series, val.value), pd.Series([4]), check_names=False
        )
