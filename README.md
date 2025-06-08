#Helpful information to understand how to use these models

### How to execute the models on Docker
1 - git clone https://github.com/diego-rossi-01/Combinatorial_Decision_Making_and_Optimization.git

2 - cd 'working_directory'

3 - docker build --no-cache 'image_name' .

4 - docker run --rm 'image_name'

### Additional Clarifications
1 - We're aware that there are two different folders containing instances in .dat format. Please use original_instances when checking the solutions with check_solution.py as it contains all the instances we're using in the program.

2 - Sometimes github automatically changes the format of file entrypoint.sh line endings, please verify that it is in LF format before running the docker build line.
