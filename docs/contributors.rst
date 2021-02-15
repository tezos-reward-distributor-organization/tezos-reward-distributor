For Developers
=====================================================

If you are interested in improving our project, this is just great! Our community looks forward to your contribution. Please follow this process:

1. Start a bug/feature issue on GitHub about your proposed change. Continue discussion until a solution is decided.
2. Use a suitable code editor like Visual Studio Code or PyCharm. If you want to work on the documentation, please use a suitable plugin for .rst files. Make sure to install recommonmark (pip install recommonmark) and the Sphinx theme (pip install sphinx_rtd_theme) when working on the documentation. Also make sure to that lines will wrap at the viewport width.
3. Fork the repo. Create a new branch from your fork for your contribution to make it easier to merge your changes back.
4. Branches MUST have descriptive names that start with either the `fix/` or `feature/` prefixes. Good examples are: `fix/signin-issue` or `feature/issue-templates`.
5. Make your changes on the branch you created in Step 2. Be sure that your code passes existing unit tests. Please add unit tests for your work if appropriate. It usually is.
6. Be sure your code style adheres to the Python PEP8 standard. Use `pycodestyle` to verify before submitting.
7. Push your changes to your fork/branch in GitHub. Rebase from the origin master before you create the PR. Don't push it to your master! If you do it will make it harder to submit new changes later.
8. Submit a pull request to the TRD repository from your commit page on GitHub.
    a. Give a descriptive title to your PR and mark it e.g. as `[WIP]` if you want it to be visible but you are not finished yet or need help.
    b. Provide a description of your changes according to the PR template.
    c. Put `closes #XXXX` in your comment to auto-close the issue that your PR fixes (if such).


Principles on the application evolution:

1. Discuss the solution with repository owners and other community members. Start the development after everybody agrees on a solution. 
2. Prefer the simpler solution. Try to make as few changes as possible. 
3. Update documentation wherever it is meaningful.
4. Create and run unit tests for the changes. Please do not sends PRs for untested changes. Payment domain requires the utmost responsibility.
5. Follow existing naming conventions.
6. Avoid code repetition. Make use of Object Oriented design principles when possible. 
7. More configuration parameters do not always mean more flexibility. We do not want the application to turn into configuration hell which nobody can use.
8. The idea of community members is very important because this repo is just a sequence of statements if nobody uses and benefit.
9. A change will be accepted if it will benefit the community. Particular requests which only very few people will take advantage will not be accepted to leave the code as simple as possible.

Disclaimer: This project started in the spirit of free and open source software with voluntary contributions without compensation.
You can always donate your contribution free of charge!


Guidelines for rewarding PRs in the context of the TRD grant:

1. Payments are not granted for contributions being paid in the context of another grant or company income.
2. The contributor should respect the process preceding a PR (start an issue and create a branch) and submit a PR in accordance with the PR template.
3. The PR can only be merged if approved by at least one maintainer. Before approving a PR, the issue should be fully solved and the changes should be tested and documented.
4. The PR can only be approved if an agreement about the work effort (in hrs) is made.
5. The PR should be merged using a squash merge, the work effort of the contributor and reviewer should be documented in the squash merge commit message.
6. The work efforts are paid out in a regular basis. The payments are documented in a dedicated file named `contributor_payments.csv`.
7. For each payment, the reason for payment should be documented (commit hash, review efforts, etc.). Additionally, the paid amount in USD, the VWAP XTZ-USD on the payment day, the payed amount in XTZ and the transaction hash are documented.