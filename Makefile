-include ./mymakefile

pylint:
	find apis authorize commons configs console deploys fixtures -iname "*.py" | xargs pylint -E

test: clean mkresultdir
	CONSOLE_DEBUG=1 py.test --junit-xml=unitTestResults/result.xml

test-cov: clean mkresultdir
	- rm -f .coverage
	- rm -rf htmlcov
	CONSOLE_DEBUG=1 py.test -vvvv --cov-report html --cov-report=term --cov=apis --cov=deploys --cov=console

mkresultdir:
	- mkdir -p unitTestResults htmlcov
	- rm -rf unitTestResults/* htmlcov/*

clean:
	- find . -iname "*__pycache__" | xargs rm -rf
	- find . -iname "*.pyc" | xargs rm -rf
