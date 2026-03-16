import os
from typing import Set, List

class Watcher:
    def __init__(self, root_path: str = "flows/"):
        self.root_path = root_path
        # Initialize seen_directories with whatever is currently there 
        # so we only report truly "new" ones after the first scan.
        self.seen_directories = self._get_current_dirs()
    
    def _get_current_dirs(self) -> Set[str]:
        """Helper to list directories in the root path."""
        try:
            return {
                d for d in os.listdir(self.root_path) 
                if os.path.isdir(os.path.join(self.root_path, d))
            }
        except FileNotFoundError:
            print(f"Warning: The directory '{self.root_path}' does not exist.")
            return set()
        
    def reset(self) -> None:
        """
        Clears the internal register of seen directories. 
        The next call to watch() will treat all existing folders as 'new'.
        """
        self.seen_directories.clear()
    
    def watch(self) -> List[str]:
        """
        Identifies new directories since the last scan and updates the register.
        :return: A list of newly discovered directory names.
        """
        current_state = self._get_current_dirs()
        
        # Calculate the difference using set subtraction
        new_dirs: Set[str] = current_state - self.seen_directories
        
        # Internal update of the seen register
        self.seen_directories.update(new_dirs)
        
        return list(new_dirs)