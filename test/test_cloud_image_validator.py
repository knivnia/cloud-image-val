import os

import pytest

from main.cloud_image_validator import CloudImageValidator
from cloud.terraform.terraform_configurator import TerraformConfigurator
from cloud.terraform.terraform_controller import TerraformController
from result.reporter import Reporter
from test_suite.suite_runner import SuiteRunner


class TestCloudImageValidator:
    test_resources_file = '/fake/test/resources_file.json'
    test_output_file = '/fake/test/output_file.xml'
    test_parallel = True
    test_debug = True
    test_instances = ['test-instance-1', 'test-instance-2']

    @pytest.fixture
    def validator(self):
        return CloudImageValidator(self.test_resources_file,
                                   self.test_output_file,
                                   self.test_parallel,
                                   self.test_debug)

    def test_main(self, mocker, validator):
        # Arrange
        test_controller = 'test controller'

        mock_initialize_infrastructure = mocker.MagicMock(return_value=test_controller)
        validator.initialize_infrastructure = mock_initialize_infrastructure

        mock_deploy_infrastructure = mocker.MagicMock(return_value=self.test_instances)
        validator.deploy_infrastructure = mock_deploy_infrastructure

        mock_run_tests_in_all_instances = mocker.MagicMock()
        validator.run_tests_in_all_instances = mock_run_tests_in_all_instances

        mock_report_test_results = mocker.MagicMock()
        validator.report_test_results = mock_report_test_results

        mock_cleanup = mocker.MagicMock()
        validator.cleanup = mock_cleanup

        # Act
        result = validator.main()

        # Assert
        assert result is None

        mock_initialize_infrastructure.assert_called_once()
        mock_deploy_infrastructure.assert_called_once()
        mock_run_tests_in_all_instances.assert_called_once_with(self.test_instances)
        mock_report_test_results.assert_called_once()
        mock_cleanup.assert_called_once()

    def test_initialize_infrastructure(self, mocker, validator):
        # Arrange
        mocker.patch('lib.ssh_lib.generate_ssh_key_pair')
        mock_get_cloud_provider_from_resources = mocker.patch.object(TerraformConfigurator,
                                                                     'get_cloud_provider_from_resources')
        mock_configure_from_resources_json = mocker.patch.object(TerraformConfigurator,
                                                                 'configure_from_resources_json')
        mock_print_configuration = mocker.patch.object(TerraformConfigurator,
                                                       'print_configuration')
        mock_initialize_resources_dict = mocker.patch.object(TerraformConfigurator,
                                                             '_initialize_resources_dict')

        # Act
        validator.initialize_infrastructure()

        # Assert
        mock_get_cloud_provider_from_resources.assert_called_once()
        mock_configure_from_resources_json.assert_called_once()
        mock_print_configuration.assert_called_once()
        mock_initialize_resources_dict.assert_called_once()

    def test_deploy_infrastructure(self, mocker, validator):
        # Arrange
        mocker.patch.object(TerraformConfigurator, 'cloud_name', create=True)

        mock_create_infra = mocker.patch.object(TerraformController,
                                                'create_infra')
        mock_get_instances = mocker.patch.object(TerraformController,
                                                 'get_instances',
                                                 return_value=self.test_instances)
        mock_generate_instances_ssh_config = mocker.patch('lib.ssh_lib.generate_instances_ssh_config')

        validator.infra_controller = TerraformController(TerraformConfigurator)

        # Act
        result = validator.deploy_infrastructure()

        # Assert
        assert result == self.test_instances

        mock_create_infra.assert_called_once()
        mock_get_instances.assert_called_once()
        mock_generate_instances_ssh_config.assert_called_once_with(instances=self.test_instances,
                                                                   ssh_config_file=validator.ssh_config_file,
                                                                   ssh_key_path=validator.ssh_identity_file)

    def test_run_tests_in_all_instances(self, mocker, validator):
        mocker.patch.object(TerraformConfigurator, 'cloud_name', create=True)
        validator.infra_configurator = TerraformConfigurator

        mocker.patch('time.sleep')
        mock_run_tests = mocker.patch.object(SuiteRunner, 'run_tests')

        validator.run_tests_in_all_instances(self.test_instances)

        mock_run_tests.assert_called_once_with(validator.output_file)

    def test_report_test_results(self, mocker, validator):
        mock_generate_html_report = mocker.patch.object(Reporter, 'generate_html_report')

        validator.report_test_results()

        mock_generate_html_report.assert_called_once_with(validator.output_file.replace('xml', 'html'))

    def test_destroy_infrastructure(self, mocker, validator):
        mock_destroy_infra = mocker.patch.object(TerraformController, 'destroy_infra')
        validator.infra_controller = TerraformController

        mock_os_remove = mocker.patch('os.remove')

        validator.cleanup()

        mock_destroy_infra.assert_called_once()

        calls = [
            mocker.call(validator.ssh_identity_file),
            mocker.call(validator.ssh_pub_key_file),
        ]
        assert mock_os_remove.call_args_list == calls
