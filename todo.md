# todo

Can you exand the dobby skills?

I want these skills to support both Azure DevOps and GitHub. 

Each project is targetting either Azure DevOps or Github; I want this stored in the project settings. If the value is not there ask for it.
Those project level settings should be used in all functions to target the right system. 
Whether it's Azure DevOps. With Pbis and boards, or Github with issues I want it to work.
So I think you can use the word pbi and issue interchangeable.

This duality is an important future requirement; just like I want to use skills with multiple cli's.

--- 

# generate specific skills

Each project is targetting either Azure DevOps or Github; or a combination of the two. I want this stored in the project settings. 

Can you create a generator, to generate the skills for the specific scenario, so we don't need to support nested skills like we do now.

Generate specific skills for the different scenario's

make a skill generator, that makes specific skills from a configuration. This should be a command line tool somehow; E.g. I like the openspec init command. Something similar, asking the scenario's.

As part of the project I want to have a generator that generates each scenario; in a build folder.


repo
- azure devops (ADO)
- github

pbi's
- github issues
- azure devops boards

Currently I see these scenarios:
1. Azure only
Git Repo: ADO
PBI's: ADO
Pull requests: ADO

2. Github only
Git Repo: Github
PBI's: Github issues
Pull requests: Github

3. ADO and Github
Git Repo: Github
PBI's: ADO
Pull requests: Github

Grill these scenrario's

