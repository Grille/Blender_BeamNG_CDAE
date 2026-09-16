type Tuple2F = tuple[float, float]
type Tuple3F = tuple[float, float, float]
type Tuple4F = tuple[float, float, float, float]

type SDict[T] = dict[str, T]

type SocketAccessor = str | int
type SocketValue = bool | float | int | Tuple3F | Tuple4F | str