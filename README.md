<!-- Throughout this template:

* Replace references in brackets and to Product[Name, Acronym, etc] with product name, acronym or other content specific to your VA product
* Throughout this file, replace bracketed information with reply to prompt within those brackets
* Review template guidance provided as 'hidden text'
* Do not delete bracket-parenthesis combinations--these create dynamic hyperlinks [display information gets typed into brackets](URL information gets typed into parentheses), as in [github-repository-name](https://github.ec.va.gov/EPMO/github-repository-name) or [John Smith](mailto:John.Smith33@va.gov); simply add product-specific information to create the links you need  

Markdown Language resources are provided here for your convenience:
* [https://www.markdownguide.org/basic-syntax](https://www.markdownguide.org/basic-syntax)
* [https://www.markdownguide.org/cheat-sheet/](https://www.markdownguide.org/cheat-sheet/)
* [https://www.markdownguide.org/extended-syntax/](https://www.markdownguide.org/extended-syntax/)
* [https://github.com/markdown-templates/markdown-emojis](https://github.com/markdown-templates/markdown-emojis)

> **How to use this template:**
> 1. Fill in the configuration block at the top of this file
> 2. Use Find & Replace (Ctrl+H) to swap all `{{TOKEN}}` placeholders throughout the file
> 3. Uncomment and complete any optional sections you need
> 4. Complete any TODOs in the file, including copying and pasting information from VASI and other sources as needed
> 5. Work through the [README Completion Checklist](#readme-completion-checklist)
> 6. Delete all template guidance comments before publishing

-->

<!--
================================================================
TEMPLATE CONFIGURATION — Fill out this block first, then use
Find & Replace (Ctrl+H) to swap placeholders throughout the file.
================================================================
Product Full Name:     {{PRODUCT_NAME}}
Product Acronym:       {{PRODUCT_ACRONYM}}
VASI ID:               {{VASI_ID}}
VASI URL:              {{VASI_URL}}
Product Line:          {{PRODUCT_LINE}}
Primary Contact Name:  {{CONTACT_NAME}}
Primary Contact Email: {{CONTACT_EMAIL}}
================================================================
-->

# {{PRODUCT_NAME}} source-code repository

This repository houses and source-controls {{PRODUCT_NAME}} product source-code files. For additional, associated {{PRODUCT_NAME}} repositories (including product documentation), see the _Additional {{PRODUCT_NAME}} repositories_ section below.

Information about how to develop changes for the {{PRODUCT_NAME}} product can be found in this repository's [CONTRIBUTING file](CONTRIBUTING.md).

:exclamation: _This readme file contains product-specific information. To update this `README.md` file, create a separate, release-level branch using a branch naming format like `{{PRODUCT_ACRONYM}}-upd-readme-file`. Make changes only on that branch, then when ready, create a pull request and follow the repository's review and promotion standard._

## Who should read this

- Engineers and developers contributing source code to the {{PRODUCT_NAME}} product.
- Configuration managers and release engineers responsible for branching, reviews, and promotions.
- Project and product team members who need to understand how {{PRODUCT_NAME}} source is organized, governed, and accessed.

## Prerequisites

- Confirm you have access to the required VA GitHub organization and {{PRODUCT_NAME}} GitHub team.
- Review the [CONTRIBUTING file](CONTRIBUTING.md) for workflow and coding standards.
- Create a feature branch from the agreed integration branch.
- Implement and test your changes.
- Open a pull request following the review and promotion standard.

## README Completion Checklist
> Remove this section before publishing.

- [ ] Replaced all `{{PRODUCT_NAME}}` references
- [ ] Replaced all `{{PRODUCT_ACRONYM}}` references
- [ ] Added product description from VASI
- [ ] Filled in `{{VASI_ID}}` and `{{VASI_URL}}`
- [ ] Listed all additional repositories
- [ ] Added contributor team contacts
- [ ] Documented repository folder structure
- [ ] Confirmed branching strategy section
- [ ] Removed all template comments and placeholders

## Product information

- Product name: VA-{{PRODUCT_NAME}}
- Abbreviation: {{PRODUCT_ACRONYM}}
- Product VASI ID: [{{VASI_ID}}]({{VASI_URL}}) <!-- TODO: Replace {{VASI_URL}} with the URL to your VA product's VASI page -->
- Product line portfolio: {{PRODUCT_LINE}}

## Product description

<!-- TODO: Copy and paste product description from VASI entry (https://vaww.vear.ea.oit.va.gov/#system_and_application_domain_vasystems_na.htm). -->
_[Insert product description here from VASI entry (https://vaww.vear.ea.oit.va.gov/#system_and_application_domain_vasystems_na.htm).]_

<details><summary><b>Additional {{PRODUCT_NAME}} repositories</b></summary>
<p>

VA standards require changes to VA product configuration items to be controlled in a VA-authorized source control management tool (like GitHub). Additional {{PRODUCT_NAME}} product source repositories are located here:

* [{{PRODUCT_ACRONYM}}-source1](https://github.ec.va.gov/EPMO/{{PRODUCT_ACRONYM}}-source1)
* [{{PRODUCT_ACRONYM}}-source2](https://github.ec.va.gov/EPMO/{{PRODUCT_ACRONYM}}-source2)
* [{{PRODUCT_ACRONYM}}-source3](https://github.ec.va.gov/EPMO/{{PRODUCT_ACRONYM}}-source3)
<!-- TODO: Replace or remove unused source repository entries above -->

{{PRODUCT_NAME}} also has a dedicated product documentation repository located here: [{{PRODUCT_ACRONYM}}-product]({{REPO_URL}}).

Access to {{PRODUCT_NAME}} repositories is granted through membership in a {{PRODUCT_NAME}} GitHub team. To request access to any {{PRODUCT_NAME}} repository, contact [{{CONTACT_NAME}}](mailto:{{CONTACT_EMAIL}}?subject=Request%20for%20{{PRODUCT_ACRONYM}}%20Repository%20Access).

</p>
</details>

<details><summary><b>{{PRODUCT_NAME}} tools</b></summary>
<p>

Project teams seeking to make changes to {{PRODUCT_NAME}} use a common set of tools for product development.
<!--
Below is an example of commonly used tools that can be used or modified as needed.

* _Jira_ - lifecycle change management tool
* _GitHub_ - source control management tool
* _Tool-Name_ - purpose-of-tool
* _Tool-Name_ - purpose-of-tool
-->

🛎️ Any team can request tools and Configuration Management support from the Configuration Management Department (CMD) by submitting a resource request here: [Request CMD support](https://forms.office.com/Pages/ResponsePage.aspx?id=Ixtf6a-r7kWCHberJRqzv7lc3RkvtzRNgphafY7z9JpUMFpLMDJEMTlFUk82OVozTTk1OEVQRUszVi4u).

Teams also agree to a workflow-change management process established by the {{PRODUCT_LINE}} product line.

</p>
</details>

## Repository contributor team contacts

Project teams contributing changes to {{PRODUCT_NAME}} product source should list their team contacts here.

✏️ For a listing of product line team contacts, see the {{PRODUCT_NAME}} VASI entry [{{VASI_ID}}]({{VASI_URL}}). <!-- TODO: Replace {{VASI_URL}} with the URL to your VA product's VASI page. --> Also consult your project management plan for product development team roster. Note that some products will have multiple projects or contracts working on the same VA product. All contributing teams should be listed in this section.

<details><summary><b>{{TEAM_NAME}}</b></summary>
<p>

List team name and points of contact who can address questions about your team's contributions to this repository.

- Project Manager: [{{CONTACT_NAME}}](mailto:{{CONTACT_EMAIL}})
- Operations Manager: [{{CONTACT_NAME}}](mailto:{{CONTACT_EMAIL}})
- Technical Lead: [{{CONTACT_NAME}}](mailto:{{CONTACT_EMAIL}})
- Development Team Manager: [{{CONTACT_NAME}}](mailto:{{CONTACT_EMAIL}})
- Configuration Manager: [{{CONTACT_NAME}}](mailto:{{CONTACT_EMAIL}})
- Team GitHub Lead: [{{CONTACT_NAME}}](mailto:{{CONTACT_EMAIL}})
- Group email: [{{GROUP_EMAIL_NAME}}](mailto:{{GROUP_EMAIL_ADDRESS}})

</p>
</details>

## Getting started with {{PRODUCT_NAME}} source files

The {{PRODUCT_NAME}} product must be developed collaboratively and transparently within this repository. Technical reviews for all {{PRODUCT_NAME}} product development efforts can be conducted here. To best fulfill this responsibility and handle merge conflicts between versions of source files that may occur, project teams adhere to the following standards and general guidance.

<details><summary><b>Product lifecycle – change management</b></summary>
<p>

Changes to files in this repository require an authorizing work record from a VA-authorized change management tool (Jira, Azure DevOps, GitHub, other). Such work records contain technical information about the changes requested and justify changes that will be made in this repository. Project teams collaborating in this repository follow current VA change management guidance.

<!--TODO:
The following change management tool information is needed. Below is an example for Jira that can be used or modified as needed.

##### Product lifecycle management tool – Jira

- JIRA Project Page: [{{PRODUCT_NAME}}](https://jira.devops.va.gov/projects/{{JIRA_KEY}}/summary)
- JIRA Project Lead: [{{CONTACT_NAME}}](mailto:{{CONTACT_EMAIL}}?subject=Request%20for%20{{PRODUCT_ACRONYM}}%20JIRA%20Project%20Support)
- JIRA Project Key: {{JIRA_KEY}}
- {{PRODUCT_NAME}} Confluence: [{{PRODUCT_NAME}} Confluence page](https://confluence.devops.va.gov/display/VAExternal/VA+OIT+DevSecOps+Product+Management)
- JIRA Access Request: [DOTS Service Desk](https://jira.devops.va.gov/servicedesk/customer/portal/43/create/682)
- DOTS Service Desk – Jira support: [DOTS Service Desk – Jira Support Portal](https://jira.devops.va.gov/servicedesk/customer/portal/1)
-->

</p>
</details>

<details><summary><b>{{PRODUCT_NAME}} source repository access</b></summary>
<p>

The Configuration Management Department (CMD) has recommended procedures for adding teams and gaining access to VA GitHub. They are explained in detail at the following link: [2.04 CMD GitHub Access and Teams Guidance](https://dvagov.sharepoint.com/sites/OITEPMOCMDepartment/SitePages/2.04-CMD-SPA-GitHub-Access-and-Teams-Guidance.aspx).

</p>
</details>

<details><summary><b>Structure of the {{PRODUCT_NAME}} source repository</b></summary>
<p>

Project teams collaborating in this repository comply with an agreed-upon repository folder structure so that anyone who needs to find a file knows where to look for it.

```
docs/        # Only source-specific documentation goes here; product documentation goes in the product documentation repository
FolderName1/ # Provide brief explanation of types of files that can be found here
FolderName2/ # Provide brief explanation of types of files that can be found here
```

🛎️ For {{PRODUCT_NAME}} development standards, conventions, and other guidance, contact your project team technical lead.

</p>
</details>

<details><summary><b>Branching strategy</b></summary>
<p>

A repository branching strategy contains not only the creation of branches but also branch workflow, branch rules, and the implementation of pull requests to support a review and promotion standard.

For CMD branch strategy guidance, see [2.05 CMD Repository Branching Guidance](https://dvagov.sharepoint.com/sites/OITEPMOCMDepartment/SitePages/2.05-CMD-SPA-Repository-Branching-Guidance.aspx). In this guidance, CMD recommends a branching strategy that promotes and synchronizes between master, integration, release, and feature branches. This branching strategy makes concurrent content development possible within this repository.

🛎️ CMD recommends displaying a branching strategy image in this section. CMD provides examples of a branching strategy images that can be found in the .cmd folder under this repository. If you need assistance diagramming a branching strategy for your product code repository, submit a resource request here: [Request CMD support](https://forms.office.com/Pages/ResponsePage.aspx?id=Ixtf6a-r7kWCHberJRqzv7lc3RkvtzRNgphafY7z9JpUMFpLMDJEMTlFUk82OVozTTk1OEVQRUszVi4u).

</p>
</details>

<details><summary><b>Branch types</b></summary>
<p>

Using a standard set of repository branch types supports both concurrent (changes to files of the same work effort) and parallel development (changes to files between separate work efforts).

For CMD branch type guidance, see [2.05 CMD Repository Branching Guidance](https://dvagov.sharepoint.com/sites/OITEPMOCMDepartment/SitePages/2.05-CMD-SPA-Repository-Branching-Guidance.aspx).

<!--
##### {{PRODUCT_NAME}} branch type guidance

This repository's workflow moves through four types of branches: production-ready, integration, release, and feature. The master branch of this repository holds production-ready files; files on master are deployable.

✏️ The default branch of a GitHub repository may be named 'master' or 'main'. For the purposes of this README file, the default branch is referred to as 'master'.

The integration branch protects the master branch. Both master and integration branches are persistent branches. New source files and/or updates to existing source files are developed in temporary branches that get created from the integration branch. Depending on the agreed-upon workflow, repositories may have one or two types of temporary branches. The first type of temporary branch is the _release branch_; release branches get created from the integration branch. The second type of temporary branch is the _feature branch_. Feature branches get created from the release branch to which they contribute when a project team needs to support concurrent development.

<!-- TODO: Replace examples below with {{PRODUCT_NAME}}-specific branch name examples -->

Purpose | Type | Created from | Name(s)/Example(s)
--------|------|--------------|-------------------
master | permanent (default) | repository template | master<br>main
integration | permanent | master (or main) | integration<br>preprod
release | temporary | integration | {{PRODUCT_ACRONYM}}-11.3.0.3
feature | temporary | release | 21167-lm-{{PRODUCT_ACRONYM}}-11.3.0.3-[brief-overview-of-work-being-done]

:pencil2: The feature branch is an optional temporary branch type used by project teams to support concurrent development within the repository.

✏️ Release branches remain available for a pre-determined warranty/compliance period (standard 90 days) before being deleted by designated project team POCs. Any branch remaining in the repository after the warranty period can be archived-deleted.
-->

</p>
</details>

<details><summary><b>Branch naming convention</b></summary>
<p>

Using a branch naming convention lets repository contributors easily identify other contributors who are working alongside them—concurrently or in parallel—within the repository.

For CMD branch naming convention guidance, see the _Defining a branch naming convention_ section of [2.05 CMD Repository Branching Guidance](https://dvagov.sharepoint.com/sites/OITEPMOCMDepartment/SitePages/2.05-CMD-SPA-Repository-Branching-Guidance.aspx).

<!--
##### {{PRODUCT_NAME}} branch naming guidance

For release branches, use the format {{PRODUCT_ACRONYM}}-[Major#.minor#.Patch#.Build#], as in: `{{PRODUCT_ACRONYM}}-11.3.0.3`.

For feature branches, use the format [work item#]-[initials]-[{{PRODUCT_ACRONYM}}]-[M.m.P.B]-[brief-overview-of-work-being-done], as in: `21167-lm-{{PRODUCT_ACRONYM}}-11.3.0.3-security-updates`.

<!-- TODO: Replace examples below with {{PRODUCT_NAME}}-specific branch name examples -->

Purpose | Branch naming convention
--------|-------------------------
master | master<br>main
integration | integration<br>preprod
release | {{PRODUCT_ACRONYM}}-11.3.0.3
feature | 21167-lm-{{PRODUCT_ACRONYM}}-11.3.0.3-[brief-overview-of-work-being-done]
-->

</p>
</details>

<details><summary><b>Review and promotion standard</b></summary>
<p>

A standard review and promotion process ensures that product changes for delivery get where they need to go when they need to be there. In GitHub, pull requests are the mechanism by which teams actualize National Institute of Standards and Technology (NIST) CM-6 and SA-10 security controls.

##### {{PRODUCT_NAME}} pull request and review guidance

🛎️ For assistance with devising and documenting pull request and review guidance for a VA product, contact the Configuration Management Department (CMD) here: [Request CMD support](https://forms.office.com/Pages/ResponsePage.aspx?id=Ixtf6a-r7kWCHberJRqzv7lc3RkvtzRNgphafY7z9JpUMFpLMDJEMTlFUk82OVozTTk1OEVQRUszVi4u).

</p>
</details>

Need support? [Request CMD support](https://forms.office.com/Pages/ResponsePage.aspx?id=Ixtf6a-r7kWCHberJRqzv7lc3RkvtzRNgphafY7z9JpUMFpLMDJEMTlFUk82OVozTTk1OEVQRUszVi4u).
