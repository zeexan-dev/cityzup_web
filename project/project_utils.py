import random
import string
import time

class FileUtils:
    @staticmethod
    def generate_unique_filename(filename):
        """
        Generate a unique filename using the current timestamp and a random string.
        
        :param filename: Original filename
        :return: Unique filename
        """
        # Generate a random string of fixed length
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        # Extract the file extension
        ext = filename.rsplit('.', 1)[1].lower()
        # Create a unique filename using timestamp and random string
        unique_filename = f"{int(time.time())}_{random_str}.{ext}"
        return unique_filename
