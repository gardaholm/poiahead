from gpx_parser import GPXParser
import time
import os


def test_gpx_parser():
    """
    Test Backend Requirement 1: GPX parsing within 2 seconds.
    
    Parses a 2MB GPX file with 20,000+ points.
    """
    test_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    file_path = os.path.join(test_dir, 'tests', 'files', 'test_file_2MB.gpx')
    with open(file_path,'rb') as file:
        gpx_byte = file.read()
    start_time = time.time()
    gpx_parser = GPXParser(gpx_byte)
    gpx_parser.parse()
    end_time = time.time()
    total_time = end_time - start_time
    assert total_time < 2
