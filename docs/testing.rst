Test structure
====================

The tests in TRD are run in the following order:
1. unit tests

2. regression tests

3. integration tests

4. smoke tests

5. acceptance tests (WIP)

6. non functional tests. (WIP)

7. formal verification (WIP)

Unit tests
--------------
Unit tests test only one specific function or method of a class. 
The smaller the function and the more specialized it is the better the unit test.

Regression tests
------------------
Regression tests are tests which document fixed bugs.
To implement a regression test you need to do the following:

1. Have a bug in trd (see bug label in issues)

2. Reproduce the bug in a test under the `regression/` directory.

3. Assert the behaviour which you would like this bug to have.

4. Fix the bug and make the test pass.

Integration tests
-------------------
Integration tests test the behaviour of trd. Meaning it tests the interaction between multiple functions or classes.

Smoke tests
-------------------
Smoke tests test if trd starts, runs and ends under different cirumstances.

Acceptance test (WIP)
-----------------------
Acceptance tests test the functionality which users are expecting to work. 
E.g. the correct and reliable distribution of rewards.

Non functional tests (WIP)
---------------------------
Non functional tests test the performance, load time, transaction speed etc. of trd.

Verification (WIP)
-------------------
Checking the FSM model systematically with exhaustive exploration. 
This consists of exploring all states and transitions in the model (`source`_).

.. _source: https://en.wikipedia.org/wiki/Formal_verification