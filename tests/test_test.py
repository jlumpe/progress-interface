from progress_interface.test import TestProgressMonitor, capture_progress


def test_capture_progress():
	"""Test the capture_progress() function."""
	config, instances = capture_progress(TestProgressMonitor.config())
	assert instances == []

	instance1 = config.create(10)
	assert instances == [instance1]

	instance2 = config.create(20)
	assert instances == [instance1, instance2]

	instance3 = config.create(30)
	assert instances == [instance1, instance2, instance3]
