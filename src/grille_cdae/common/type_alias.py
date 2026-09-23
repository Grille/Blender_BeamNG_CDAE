type Tuple2F = tuple[float, float]
type Tuple3F = tuple[float, float, float]
type Tuple4F = tuple[float, float, float, float]

type Tuple2I = tuple[int, int]
type Tuple3I = tuple[int, int, int]
type Tuple4I = tuple[int, int, int, int]

type SDict[T=object] = dict[str, T]

type SocketAccessor = str | int
type SocketValue = bool | float | int | Tuple2F | Tuple3F | Tuple4F | str