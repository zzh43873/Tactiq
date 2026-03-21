// Type declarations for react-simple-maps (no @types package available)
/// <reference types="react" />

declare module 'react-simple-maps' {
  import type { CSSProperties, MouseEvent, ReactNode, FC } from 'react'

  interface GeographyProps {
    geography: any
    fill?: string
    stroke?: string
    strokeWidth?: number
    style?: {
      default?: CSSProperties
      hover?: CSSProperties
      pressed?: CSSProperties
    }
    onClick?: (event: MouseEvent) => void
  }

  interface GeographiesProps {
    geography: string | object
    children: (props: { geographies: any[] }) => ReactNode
    onError?: () => void
    onLoad?: () => void
  }

  interface MarkerProps {
    coordinates: [number, number]
    children?: ReactNode
    onClick?: () => void
  }

  interface ZoomableGroupProps {
    zoom?: number
    center?: [number, number]
    minZoom?: number
    maxZoom?: number
    onMoveEnd?: (props: { coordinates: [number, number]; zoom: number }) => void
    children?: ReactNode
  }

  interface ComposableMapProps {
    projection?: string
    projectionConfig?: {
      scale?: number
      center?: [number, number]
    }
    style?: CSSProperties
    children?: ReactNode
  }

  export const Geography: FC<GeographyProps>
  export const Geographies: FC<GeographiesProps>
  export const Marker: FC<MarkerProps>
  export const ZoomableGroup: FC<ZoomableGroupProps>
  export const ComposableMap: FC<ComposableMapProps>
}
