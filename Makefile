pre-commit:
	pre-commit run --all-files

test: unittest

unittest:
	pytest

coverage:
	pytest --cov-report html --cov-report xml

tdd:
	ptw
