@echo off

rem ~dp0 means 'the directory where this file is located'
rem $Id:$
cd %~dp0\..
java -Djava.ext.dirs=home;lib;lib\thirdparty_include;lib\oaa2.3.2 -Xss1024k -Xmx256M -Dpython.home=home -Dpython.path=src -Dspark.modules=%SPARK_MODULES%  com.sri.ai.spark.runtime.Spark %*
