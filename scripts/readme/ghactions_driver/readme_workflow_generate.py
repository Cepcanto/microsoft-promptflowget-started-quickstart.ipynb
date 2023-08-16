from pathlib import Path

from .readme_step import ReadmeStepsManage, ReadmeSteps


def write_readme_workflow(readme_path):
    relative_path = Path(readme_path).relative_to(
        Path(ReadmeStepsManage.git_base_dir())
    )
    workflow_path = relative_path.as_posix()
    relative_name_path = Path(readme_path).relative_to(
        Path(ReadmeStepsManage.git_base_dir()) / "examples"
    )
    workflow_name = relative_name_path.as_posix().replace("/", "_").replace("-", "_")
    workflow_name = "samples_" + workflow_name

    ReadmeSteps.setup_target(
        workflow_path,
        "basic_workflow_replace.yml.jinja2",
        f"{workflow_name}.yml",
    )
    ReadmeSteps.install_dependencies()
    ReadmeSteps.install_dev_dependencies()
    ReadmeSteps.create_env()
    if workflow_name.endswith("pdf"):
        ReadmeSteps.env_create_aoai("chat_with_pdf_custom_connection")
    ReadmeSteps.create_run_yaml()
    if (
        workflow_name.endswith("flows_standard_basic_with_builtin_llm")
        or workflow_name.endswith("flows_standard_flow_with_symlinks")
        or workflow_name.endswith("flows_standard_flow_with_additional_includes")
        or workflow_name.endswith("flows_standard_basic_with_connection")
    ):
        ReadmeSteps.yml_create_aoai("examples/connections/azure_openai.yml")
    ReadmeSteps.azure_login()
    if workflow_name.endswith("flows_standard_summarizing_film_with_autogpt"):
        ReadmeSteps.extract_steps_and_run_gpt_four()
    else:
        ReadmeSteps.extract_steps_and_run()

    ReadmeStepsManage.write_workflow(workflow_name, "auto_generated_steps")
    ReadmeSteps.cleanup()
