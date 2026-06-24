from enum import Enum



class StrEnum(str, Enum):
    def __str__(self):
        return self.value
    


class IntEnum(int, Enum):
  def __str__(self):
      return str(self.value)
    
    

class FloatEnum(float, Enum):
  def __str__(self):
      return str(self.value)
    
    
    


